import inspect
import json
import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Sequence

import opentelemetry
from opentelemetry import trace as otel_trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,
                                            ConsoleSpanExporter,
                                            SimpleSpanProcessor)
from opentelemetry.trace import ProxyTracerProvider, get_current_span
from opentelemetry.trace.propagation.tracecontext import \
    TraceContextTextMapPropagator
from opentelemetry.util._once import Once

from rouge_ai.config import RougeConfig
from rouge_ai.constants import ENV_VAR_MAPPING
from rouge_ai.credentials import CredentialManager
from rouge_ai.integrations.llm import instrument_llm
from rouge_ai.logger import shutdown_logger
from rouge_ai.utils.config import find_rouge_config


def tracer_verbose(config: RougeConfig, message: str, *args: Any) -> None:
    """Helper function for conditional tracer debugging

    Args:
        config: RougeConfig instance
        message: Debug message to output
        *args: Additional arguments to pass to logger
    """
    if config.tracer_verbose:
        print(f"[Rouge-Tracer] {message}", *args)


def tracer_verbose_error(config: RougeConfig, message: str, *args:
                         Any) -> None:
    """Helper function for conditional tracer error debugging

    Args:
        config: RougeConfig instance
        message: Error message to output
        *args: Additional arguments to pass to logger
    """
    if config.tracer_verbose:
        print(f"[Rouge-Tracer] ERROR: {message}", *args, file=sys.stderr)


# Global state
_tracer_provider: TracerProvider | None = None
_config: RougeConfig | None = None
_credential_manager: CredentialManager | None = None
# Guards the one place that resets OTel's process-global provider.
_lock = threading.Lock()


@dataclass
class TraceOptions:
    r"""Options for configuring function tracing"""
    span_name: str | None = None
    span_name_suffix: str | None = None

    # Parameter tracking options
    trace_params: bool | Sequence[str] = False
    trace_return_value: bool = False

    # Attribute handling
    flatten_attributes: bool = True

    def get_span_name(self, fn: Callable) -> str:
        r"""Get the span name for a function"""
        if self.span_name is not None:
            return self.span_name
        if self.span_name_suffix is not None:
            return f'{fn.__module__}.{fn.__qualname__}{self.span_name_suffix}'
        return f'{fn.__module__}.{fn.__qualname__}'


def _load_env_config() -> dict[str, Any]:
    """Load and validate configuration from environment variables.

    Returns:
        Dictionary with validated config values from environment variables
    """
    from rouge_ai.utils.security import validate_config_value

    env_config = {}

    for env_var, config_field in ENV_VAR_MAPPING.items():
        value = os.getenv(env_var)
        if value is not None:
            try:
                # Handle boolean values
                if config_field in [
                        "enable_span_console_export",
                        "enable_log_console_export",
                        "enable_span_cloud_export", "enable_log_cloud_export",
                        "local_mode", "tracer_verbose", "logger_verbose",
                        "instrument_llm"
                ]:
                    env_config[config_field] = value.lower() in ('true', '1',
                                                                 'yes', 'on')
                # Handle comma-separated list values
                elif config_field in ("llm_providers", "llm_block_providers"):
                    env_config[config_field] = [
                        item.strip() for item in value.split(",")
                        if item.strip()
                    ]
                # Handle float values
                elif config_field == "traces_sampler_ratio":
                    env_config[config_field] = float(value)
                else:
                    # SECURITY FIX: Validate value before using
                    env_config[config_field] = validate_config_value(
                        config_field, value)
            except ValueError as e:
                # Log validation error and skip invalid config
                print(f"[Rouge] Invalid config for {env_var}: {e}",
                      file=sys.stderr)
                continue

    return env_config


def _create_span_exporter(config: RougeConfig):
    """Create an OTLP span exporter, choosing HTTP vs gRPC.

    Selection order: the standard ``OTEL_EXPORTER_OTLP_PROTOCOL`` env var
    (``grpc`` | ``http/protobuf``), then the endpoint URL scheme
    (``grpc``/``grpcs`` -> gRPC, ``http``/``https`` -> HTTP). Defaults to
    HTTP/protobuf. The exporter still reads ``OTEL_EXPORTER_OTLP_HEADERS`` /
    ``OTEL_EXPORTER_OTLP_TIMEOUT`` from the environment.

    pattern: openllmetry traceloop-sdk@0.61.0 tracing.py:315-354
    """
    from urllib.parse import urlparse

    endpoint = config.otlp_endpoint
    scheme = urlparse(endpoint).scheme.lower()
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "").strip().lower()

    if protocol == "grpc" or (not protocol and scheme in ("grpc", "grpcs")):
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
            OTLPSpanExporter as GRPCSpanExporter

        # grpcs => TLS; grpc (or anything else) => insecure
        insecure = scheme != "grpcs"
        target = endpoint
        if "://" in target:
            target = target.split("://", 1)[-1]
        return GRPCSpanExporter(endpoint=target, insecure=insecure)

    # Default: HTTP/protobuf
    return OTLPSpanExporter(endpoint=endpoint)


def init(**kwargs: Any) -> TracerProvider:
    r"""Initialize Rouge tracing and logging.

    This is the main entry point for setting up tracing and logging.
    Call this once at the start of your application.

    Args:
        **kwargs: Configuration parameters for RougeConfig.
            If a .rouge-config.yaml file exists, it will be loaded first,
            and any kwargs provided will override the file configuration.

    Returns:
        TracerProvider instance
    """
    global _tracer_provider, _config

    # Check if already initialized and no kwargs provided
    if _tracer_provider is not None and len(kwargs) == 0:
        return _tracer_provider

    # If kwargs are provided while already initialized, reconfigure in place:
    # refresh config + logger but REUSE the existing provider. OpenTelemetry is
    # one-provider-per-process, and recreating/clobbering it would orphan
    # tracers already held by instrumented libraries (FastAPI, LLM SDKs).
    reusing_provider = _tracer_provider is not None and len(kwargs) > 0
    if reusing_provider:
        # Logger is reinitialized with the new config (e.g. a new token).
        shutdown_logger()

    # Load configuration from YAML file first
    yaml_config = find_rouge_config()

    # Load environment variables (highest priority)
    env_config = _load_env_config()

    # Merge configs with priority: env_vars > kwargs > yaml_config
    config_params = {}
    if yaml_config:
        config_params.update(yaml_config)
    config_params.update(kwargs)
    config_params.update(env_config)  # env vars have highest priority

    # DEBUG
    print(f"DEBUG: yaml_config={yaml_config}")
    print(f"DEBUG: kwargs={kwargs}")
    print(f"DEBUG: env_config={env_config}")
    print(f"DEBUG: config_params={config_params}")

    if len(config_params) == 0:
        return

    config = RougeConfig(**config_params)

    _config = config

    tracer_verbose(
        config, "Initializing Rouge with config:", {
            "service_name": config.service_name,
            "environment": config.environment,
            "local_mode": config.local_mode,
            "enable_span_console_export": config.enable_span_console_export,
            "enable_span_cloud_export": config.enable_span_cloud_export,
            "enable_log_console_export": config.enable_log_console_export,
            "enable_log_cloud_export": config.enable_log_cloud_export,
            "tracer_verbose": config.tracer_verbose,
            "logger_verbose": config.logger_verbose
        })

    # Initialize shared credential manager
    global _credential_manager
    _credential_manager = CredentialManager(config)

    # Re-init: a provider already exists — keep it (config + logger were
    # refreshed above) and return without recreating it or touching the global.
    if reusing_provider:
        tracer_verbose(config, "Reusing existing tracer provider for re-init")
        return _tracer_provider

    # Create resource with service information
    tracer_verbose(config, "Creating OpenTelemetry resource...")

    resource_attributes = {
        SERVICE_NAME: config.service_name,
        "service.github_owner": config.github_owner,
        "service.github_repo_name": config.github_repo_name,
        "service.version": config.github_commit_hash,
        "service.environment": config.environment,
    }

    # Ensure all values are strings as OpenTelemetry requires.
    # Filter out None values.
    resource_attributes = {
        str(k): str(v)
        for k, v in resource_attributes.items()
        if v is not None and k is not None
    }

    # Resource.create merges OTel SDK defaults (telemetry.sdk.*) and the
    # standard OTEL_RESOURCE_ATTRIBUTES / OTEL_SERVICE_NAME env vars.
    resource = Resource.create(resource_attributes)

    # Create or reuse the tracer provider. Mirrors traceloop/openllmetry
    # (tracing.py:460-480): create + set the global only when none is installed
    # yet; otherwise reuse the existing provider instead of overriding the
    # global (which OpenTelemetry disallows, and which would orphan already-
    # instrumented libraries).
    # Sampler: an explicit ratio (config or ROUGE_TRACES_SAMPLER_RATIO) wins;
    # otherwise pass None so the SDK honors OTEL_TRACES_SAMPLER / its default.
    sampler = None
    if config.traces_sampler_ratio is not None:
        from opentelemetry.sdk.trace.sampling import (ParentBased,
                                                      TraceIdRatioBased)
        sampler = ParentBased(TraceIdRatioBased(config.traces_sampler_ratio))

    current_provider = otel_trace.get_tracer_provider()
    if isinstance(current_provider, ProxyTracerProvider):
        tracer_verbose(config, "Creating tracer provider...")
        provider = TracerProvider(resource=resource, sampler=sampler)
        otel_trace.set_tracer_provider(provider)
    elif hasattr(current_provider, "add_span_processor"):
        tracer_verbose(config, "Reusing existing global tracer provider...")
        provider = current_provider
    else:
        tracer_verbose(config, "Creating tracer provider...")
        provider = TracerProvider(resource=resource, sampler=sampler)
        otel_trace.set_tracer_provider(provider)

    # Add span processors based on configuration
    if config.enable_span_console_export:
        tracer_verbose(config, "Adding console span processor...")
        console_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(console_processor)

    # Only add cloud export if enabled
    if config.enable_span_cloud_export:
        tracer_verbose(config, "Setting up cloud span export...")
        # Ensure we have fresh credentials and OTLP
        # endpoint before creating exporter
        if _credential_manager:
            tracer_verbose(config, "Getting credentials for cloud export...")
            _credential_manager.get_credentials()

        tracer_verbose(
            config, f"Creating OTLP span exporter with endpoint: "
            f"{config.otlp_endpoint}")
        exporter = _create_span_exporter(config)
        batch_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(batch_processor)
        tracer_verbose(config, "Added batch span processor for cloud export")

    _tracer_provider = provider

    # Configure propagators for distributed tracing. OpenTelemetry's default
    # global propagator is already W3C tracecontext+baggage and honors
    # OTEL_PROPAGATORS, so only install ours when the user hasn't customized
    # propagation via that env var (avoids clobbering a custom setup).
    if not os.getenv("OTEL_PROPAGATORS"):
        tracer_verbose(config,
                       "Configuring propagators for distributed tracing...")
        propagator = CompositePropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])
        set_global_textmap(propagator)

    # Automatically instrument LLM providers if available
    instrument_llm(config)

    tracer_verbose(config, "Rouge initialization completed successfully")
    return provider


def _reset_global_tracer_provider() -> None:
    """Reset OpenTelemetry's process-global tracer provider.

    OpenTelemetry intentionally lets ``set_tracer_provider`` take effect only
    once and exposes no public API to replace the global provider. We clear it
    so a later ``init()`` (e.g. after ``shutdown()``) can install a fresh one.
    This is the single place that touches OTel internals; it is lock-guarded to
    stay thread-safe.
    """
    with _lock:
        otel_trace._TRACER_PROVIDER_SET_ONCE = Once()
        otel_trace._TRACER_PROVIDER = None


def shutdown_tracing() -> None:
    """
    Shutdown tracing and flush any pending spans.

    This should be called when your application is shutting down
    to ensure all traces are properly exported.
    """
    global _tracer_provider, _config, _credential_manager

    if _tracer_provider is not None:
        if _config and _config.tracer_verbose:
            tracer_verbose(_config, "Flushing and shutting down tracing...")
        _tracer_provider.force_flush()
        _tracer_provider.shutdown()
        _tracer_provider = None
        _config = None
        _credential_manager = None

    # Allow a later init() to install a fresh provider. Replaces the previous
    # set_tracer_provider(NoOpTracerProvider()) call, which was a silent no-op
    # once a real provider had already been set (and used a deprecated alias).
    _reset_global_tracer_provider()


def shutdown() -> None:
    """
    Shutdown both tracing and logging systems.

    This should be called when your application is shutting down
    to ensure all traces and logs are properly exported and to avoid
    warnings about messages sent after logging system shutdown.
    """
    shutdown_logger()
    shutdown_tracing()


def is_initialized() -> bool:
    """Check if tracing has been initialized"""
    return _tracer_provider is not None


def get_tracer(name: str | None = None) -> otel_trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Tracer name, defaults to 'rouge-ai'

    Returns:
        Tracer instance
    """
    return otel_trace.get_tracer(name or "rouge-ai")


def get_tracer_provider() -> TracerProvider | None:
    """Get the current tracer provider"""
    return _tracer_provider


def get_config() -> RougeConfig | None:
    """Get the current configuration"""
    return _config


@contextmanager
def _trace(function: Callable, options: TraceOptions, *args: Any,
           **kwargs: dict[str, Any]):
    """Internal context manager for tracing function execution"""
    # no-op if tracing is not initialized
    if not is_initialized():
        if _config and _config.tracer_verbose:
            tracer_verbose(
                _config,
                "Tracing not initialized, skipping trace for function:",
                function.__name__)
        yield None
        return

    try:
        # Get tracer instance
        tracer = opentelemetry.trace.get_tracer(__name__)

        # Get span name from options
        _span_name = options.get_span_name(function)

        if _config and _config.tracer_verbose:
            tracer_verbose(
                _config, f"Starting span: {_span_name} for function: "
                f"{function.__name__}")

        # Create and start new span
        _span = tracer.start_as_current_span(_span_name)
    except Exception as e:
        # If span creation fails, yield None and continue without tracing
        if _config and _config.tracer_verbose:
            tracer_verbose_error(
                _config,
                f"Failed to create span for function {function.__name__}: {e}")
        yield None
        return

    with _span as span:
        # Set AWS X-Ray annotations as individual attributes
        # Avoid setting hash in local mode
        if not _config.local_mode and _config._name is not None:
            span.set_attribute("hash", _config._name)
        span.set_attribute("service_name", _config.service_name)
        span.set_attribute("service_environment", _config.environment)
        span.set_attribute("telemetry_sdk_language", "python")

        if _config and _config.tracer_verbose:
            tracer_verbose(
                _config,
                f"Setting span attributes for function: {function.__name__}")

        # Add parameter attributes if requested
        if options.trace_params:
            if _config and _config.tracer_verbose:
                tracer_verbose(
                    _config,
                    f"Tracing parameters for function: {function.__name__}")
            parameter_values = _params_to_dict(
                function,
                options.trace_params,
                *args,
                **kwargs,
            )
            _store_dict_in_span(parameter_values, span,
                                options.flatten_attributes)
        yield span


def trace(options: TraceOptions = TraceOptions()) -> Callable[..., Any]:
    """
    Decorator for tracing function execution.

    Args:
        options: TraceOptions instance to configure tracing behavior

    Returns:
        Decorated function with tracing enabled

    Example:
        @trace()
        def my_function():
            pass

        @trace(TraceOptions(trace_params=True, trace_return_value=True))
        def detailed_function(x, y):
            return x + y
    """

    def _inner_trace(function: Callable) -> Callable:
        # Register the decorated function in the registry for introspection
        try:
            from rouge_ai.registry import get_registry
            registry = get_registry()
            registry.register_traced_function(function,
                                              decorator_name="trace",
                                              options=options)
        except Exception:
            # Silently fail - don't break tracing if registry fails
            pass

        @wraps(function)
        def _trace_sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _trace(function, options, *args, **kwargs) as span:
                ret = function(*args, **kwargs)
                if options.trace_return_value and span:
                    _store_dict_in_span({"return": ret}, span,
                                        options.flatten_attributes)
                return ret

        @wraps(function)
        async def _trace_async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _trace(function, options, *args, **kwargs) as span:
                ret = await function(*args, **kwargs)
                if options.trace_return_value and span:
                    _store_dict_in_span({"return": ret}, span,
                                        options.flatten_attributes)
                return ret

        @wraps(function)
        def _trace_gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            # The span must span the whole stream: a generator function returns
            # immediately, so without iterating inside the span the span would
            # end with ~0 duration and miss the streaming work.
            # pattern: openllmetry traceloop-sdk base.py:278-279
            with _trace(function, options, *args, **kwargs) as span:
                collected = [] if options.trace_return_value else None
                for item in function(*args, **kwargs):
                    if collected is not None:
                        collected.append(item)
                    yield item
                if collected is not None and span:
                    _store_dict_in_span({"return": collected}, span,
                                        options.flatten_attributes)

        @wraps(function)
        async def _trace_async_gen_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _trace(function, options, *args, **kwargs) as span:
                collected = [] if options.trace_return_value else None
                async for item in function(*args, **kwargs):
                    if collected is not None:
                        collected.append(item)
                    yield item
                if collected is not None and span:
                    _store_dict_in_span({"return": collected}, span,
                                        options.flatten_attributes)

        # Return the wrapper matching the function kind. Generators and async
        # generators are handled explicitly so streaming spans cover the full
        # iteration rather than just object creation.
        if inspect.isasyncgenfunction(function):
            return _trace_async_gen_wrapper
        elif inspect.iscoroutinefunction(function):
            return _trace_async_wrapper
        elif inspect.isgeneratorfunction(function):
            return _trace_gen_wrapper
        else:
            return _trace_sync_wrapper

    return _inner_trace


def write_attributes_to_current_span(attributes: dict[str, Any]) -> None:
    """Write custom attributes to the current active span"""
    span = get_current_span()
    if span and span.is_recording():
        _store_dict_in_span(attributes, span, flatten=False)


def _attr_value_length_limit() -> int | None:
    """Max attribute-value length from the standard OTel env var, if set."""
    raw = (os.getenv("OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT")
           or os.getenv("OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT"))
    if raw:
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _coerce_attr_value(value: Any) -> Any:
    """Coerce a value into a valid OpenTelemetry attribute value.

    OTel attributes accept only bool/str/bytes/int/float (or homogeneous
    sequences of those); anything else is dropped with a warning. Non-scalar
    values are JSON-encoded into a single string so nothing is silently lost.
    """
    if isinstance(value, bool) or type(value) in (int, float, str, bytes):
        return value
    return json.dumps(value, default=str)


def _params_to_dict(
    func: Callable,
    params_to_track: bool | Sequence[str],
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convert function parameters to dictionary for tracing"""
    try:
        bound_arguments = inspect.signature(func).bind(*args, **kwargs)
        bound_arguments.apply_defaults()

        def _should_track_key(key: str) -> bool:
            if key == 'self':
                return False
            if isinstance(params_to_track, bool):
                return params_to_track
            return key in params_to_track

        return {
            f'params.{key}': value
            for key, value in bound_arguments.arguments.items()
            if _should_track_key(key)
        }
    except Exception:
        return {}


def _store_dict_in_span(data: dict[str, Any], span: Any, flatten: bool = True):
    """Store a dictionary on a span as attributes.

    Flattens nested dicts (optional), coerces every value to a valid OTel
    attribute type, and truncates long string values to
    OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT when that env var is set.
    """
    if flatten:
        data = _flatten_dict(data)
    max_len = _attr_value_length_limit()
    attributes: dict[str, Any] = {}
    for key, value in data.items():
        coerced: Any = "None" if value is None else _coerce_attr_value(value)
        if (max_len is not None and isinstance(coerced, str)
                and len(coerced) > max_len):
            coerced = coerced[:max_len]
        attributes[str(key)] = coerced
    span.set_attributes(attributes)


def _flatten_dict(data: dict[str, Any], sep: str = "_") -> dict[str, Any]:
    """Flatten a nested dict, joining parent/child keys with ``sep``.

    Pure-Python replacement for pandas.json_normalize (drops the heavy pandas
    runtime dependency).
    """
    flattened: dict[str, Any] = {}

    def _walk(obj: dict[str, Any], parent: str) -> None:
        for key, value in obj.items():
            new_key = f"{parent}{sep}{key}" if parent else str(key)
            if isinstance(value, dict) and value:
                _walk(value, new_key)
            else:
                flattened[new_key] = value

    _walk(data, "")
    return flattened
