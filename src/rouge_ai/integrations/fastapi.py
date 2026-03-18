"""FastAPI integration for automatic request tracing"""

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Span

from rouge_ai.tracer import get_config, get_tracer_provider

# SECURITY: Sensitive headers that should be redacted
SENSITIVE_HEADERS = {
    'authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
    'x-auth-token',
    'x-csrf-token',
    'proxy-authorization',
    'x-access-token',
    'x-refresh-token',
    'api-key',
    'apikey',
    'auth-token',
    'session-id',
    'sessionid',
}

# Safe headers that can be logged
SAFE_HEADERS = {
    'content-type',
    'content-length',
    'user-agent',
    'accept',
    'accept-encoding',
    'accept-language',
    'host',
    'referer',
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-request-id',
    'x-correlation-id',
}


def sanitize_headers(headers: list) -> dict:
    """Sanitize headers before adding to span attributes.

    Args:
        headers: List of (key, value) tuples representing HTTP headers

    Returns:
        Dictionary of sanitized headers safe for telemetry
    """
    sanitized = {}

    for key, value in headers:
        # Normalize header key
        if isinstance(key, bytes):
            key_str = key.decode('utf-8', errors='ignore')
        else:
            key_str = str(key)

        key_lower = key_str.lower()

        # Redact sensitive headers
        if key_lower in SENSITIVE_HEADERS:
            sanitized[f"http.header.{key_lower}"] = "***REDACTED***"
        # Only log safe headers
        elif key_lower in SAFE_HEADERS:
            if isinstance(value, bytes):
                value_str = value.decode('utf-8', errors='ignore')
            else:
                value_str = str(value)
            sanitized[f"http.header.{key_lower}"] = value_str
        else:
            # Explicitly skip unknown headers
            pass

    return sanitized


def _sanitize_body(body: str) -> str:
    """Sanitize response/request body to remove PII and sensitive data.

    Args:
        body: The body content as a string

    Returns:
        Sanitized body with PII replaced
    """
    import re

    # PII and sensitive data patterns
    patterns = [
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        # Social Security Numbers (US)
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
        # Credit card numbers
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),
        # Phone numbers (various formats)
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
        # Password fields in JSON
        (r'"password"\s*:\s*"[^"]*"', '"password":"***"'),
        (r"'password'\s*:\s*'[^']*'", "'password':'***'"),
        # Token fields in JSON
        (r'"token"\s*:\s*"[^"]*"', '"token":"***"'),
        (r"'token'\s*:\s*'[^']*'", "'token':'***'"),
        # API key fields
        (r'"api[_-]?key"\s*:\s*"[^"]*"', '"api_key":"***"'),
        # Authorization values
        (r'"authorization"\s*:\s*"[^"]*"', '"authorization":"***"'),
    ]

    sanitized = body
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern,
                           replacement,
                           sanitized,
                           flags=re.IGNORECASE)

    return sanitized


def connect_fastapi(app: FastAPI) -> None:
    """
    Setup automatic tracing for FastAPI application with distributed tracing
    support.

    This adds middleware to automatically trace all HTTP requests,
    correlate them with logs, and properly handle incoming trace context
    from other services in a microservice architecture.

    Args:
        app: FastAPI application instance

    Example:
        import rouge_ai
        from fastapi import FastAPI
        from rouge_ai import connect_fastapi

        app = FastAPI()
        rouge_ai.init()
        connect_fastapi(app)
    """
    provider = get_tracer_provider()
    config = get_config()

    if provider is None:
        raise RuntimeError("Tracing not initialized. Call rouge_ai.init() first.")

    if config is None:
        raise RuntimeError("Configuration not available.")

    def server_request_hook(span: Span, scope: dict):
        """Hook called when server receives a request"""
        if span and span.is_recording():
            # Add service metadata to the span
            span.set_attribute("service.name", config.service_name)
            span.set_attribute("service.github_owner", config.github_owner)
            span.set_attribute("service.github_repo_name",
                               config.github_repo_name)
            span.set_attribute("service.version", config.github_commit_hash)
            span.set_attribute("service.environment", config.environment)
            span.set_attribute("telemetry.sdk.language", "python")

            # Add request path
            path = scope.get('path', '')
            if path:
                span.set_attribute("http.path", path)

            method = scope.get('method', '')
            if method:
                span.set_attribute("http.method", method)

    def client_request_hook(span: Span, scope: dict, message: dict = None):
        """Hook called when making outbound requests"""
        if span and span.is_recording():
            span.set_attribute("service.name", config.service_name)
            span.set_attribute("telemetry.sdk.language", "python")

            # Removed redundant path and method extraction as it's
            # handled in server_request_hook

            if message:
                status_code = message.get('status', '')
                if status_code:
                    span.set_attribute("http.status_code", status_code)

                # SECURITY FIX: Sanitize headers before logging
                headers = message.get('headers', [])
                assert isinstance(headers, list)
                sanitized_headers = sanitize_headers(headers)
                for key, value in sanitized_headers.items():
                    span.set_attribute(key, value)

    def client_response_hook(span: Span, scope: dict, message: dict):
        """Hook called when receiving responses from outbound requests.
        NOTE: We are not using scope here because it's the same as the
        one used in client_request_hook.
        """
        if span and span.is_recording():
            span.set_attribute("service.name", config.service_name)
            span.set_attribute("telemetry.sdk.language", "python")

            # SECURITY FIX: Only log response bodies if explicitly enabled
            if config.log_response_bodies:
                body = message.get('body', '')
                if body:
                    # Limit body preview length
                    max_length = (200
                                  if config.sanitize_telemetry_data else 1000)
                    body_str = str(body)[:max_length]

                    # Sanitize if enabled
                    if config.sanitize_telemetry_data:
                        body_str = _sanitize_body(body_str)

                    span.set_attribute("http.response.body_preview", body_str)

    # Instrument the FastAPI app
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        server_request_hook=server_request_hook,
        client_request_hook=client_request_hook,
        client_response_hook=client_response_hook,
    )
