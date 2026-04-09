"""SDK introspection engine for automatic API documentation.

This module scans the Rouge.ai SDK to discover all public APIs, decorators,
functions, and configuration options for documentation and introspection.
"""

import inspect
from typing import Any, Dict, List

from rouge_ai.config import RougeConfig
from rouge_ai.registry import get_registry
from rouge_ai.tracer import TraceOptions, trace


def _register_sdk_functions() -> None:
    """Register all SDK public functions in the registry."""
    registry = get_registry()

    # Import main module to get public functions
    import rouge_ai

    # Register main entry points
    examples_init = [
        '''import rouge_ai

# Basic initialization
rouge_ai.init(service_name="my-app")''',
        '''import rouge_ai

# With configuration
rouge_ai.init(
    service_name="my-app",
    environment="production",
    enable_span_console_export=True
)''',
    ]

    registry.register_function(
        rouge_ai.init,
        category="initialization",
        examples=examples_init,
        tags=["core", "setup", "required"],
    )

    examples_trace = [
        '''from rouge_ai import trace

@trace()
def my_function():
    return "Hello, World!"''',
        '''from rouge_ai import trace, TraceOptions

@trace(TraceOptions(trace_params=True, trace_return_value=True))
def add(x, y):
    return x + y''',
    ]

    registry.register_function(
        rouge_ai.trace,
        category="tracing",
        examples=examples_trace,
        tags=["decorator", "core", "tracing"],
    )

    examples_get_tracer = [
        '''from rouge_ai import get_tracer

tracer = get_tracer()
with tracer.start_as_current_span("my-operation"):
    # Your code here
    pass''',
    ]

    registry.register_function(
        rouge_ai.get_tracer,
        category="tracing",
        examples=examples_get_tracer,
        tags=["advanced", "tracing"],
    )

    examples_get_logger = [
        '''from rouge_ai import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.error("An error occurred", extra={"user_id": 123})''',
    ]

    registry.register_function(
        rouge_ai.get_logger,
        category="logging",
        examples=examples_get_logger,
        tags=["core", "logging"],
    )

    examples_shutdown = [
        '''import rouge_ai

# At application shutdown
rouge_ai.shutdown()''',
    ]

    registry.register_function(
        rouge_ai.shutdown,
        category="lifecycle",
        examples=examples_shutdown,
        tags=["cleanup", "shutdown"],
    )

    examples_launch_dashboard = [
        '''import rouge_ai

rouge_ai.init(service_name="my-app")
rouge_ai.launch_dashboard(port=10108)  # Starts on http://localhost:10108''',
    ]

    registry.register_function(
        rouge_ai.launch_dashboard,
        category="dashboard",
        examples=examples_launch_dashboard,
        tags=["dashboard", "visualization"],
    )

    examples_connect_fastapi = [
        '''import rouge_ai
from fastapi import FastAPI

app = FastAPI()
rouge_ai.init(service_name="my-app")
rouge_ai.connect_fastapi(app)  # Auto-traces all endpoints''',
    ]

    registry.register_function(
        rouge_ai.connect_fastapi,
        category="integration",
        examples=examples_connect_fastapi,
        tags=["fastapi", "integration", "auto-tracing"],
    )

    examples_mount_dashboard = [
        '''import rouge_ai
from fastapi import FastAPI

app = FastAPI()
rouge_ai.init(service_name="my-app")
rouge_ai.mount_dashboard(app, path="/rouge")  # Dashboard at /rouge''',
    ]

    registry.register_function(
        rouge_ai.mount_dashboard,
        category="integration",
        examples=examples_mount_dashboard,
        tags=["fastapi", "dashboard", "integration"],
    )


def _register_decorators() -> None:
    """Register all SDK decorators in the registry."""
    registry = get_registry()

    examples_trace = [
        '''from rouge_ai import trace

@trace()
def process_data(data):
    return data.upper()''',
        '''from rouge_ai import trace, TraceOptions

@trace(TraceOptions(
    span_name="custom-span",
    trace_params=True,
    trace_return_value=True
))
async def fetch_user(user_id: int):
    return {"id": user_id, "name": "John"}''',
    ]

    registry.register_decorator(
        name="trace",
        decorator_func=trace,
        options_class=TraceOptions,
        examples=examples_trace,
        category="tracing",
    )


def _register_config_fields() -> None:
    """Register all RougeConfig fields in the registry."""
    registry = get_registry()

    # Get all fields from RougeConfig dataclass
    config_fields = RougeConfig.__dataclass_fields__

    # Map environment variables
    from rouge_ai.constants import ENV_VAR_MAPPING
    env_var_reverse = {v: k for k, v in ENV_VAR_MAPPING.items()}

    # Categorize fields
    field_categories = {
        # Identification
        "service_name": ("identification", "Service name for telemetry", True),
        "github_owner": ("identification", "GitHub repository owner", False),
        "github_repo_name": ("identification", "GitHub repository name", False),
        "github_commit_hash": ("identification", "Git commit hash", False),
        "name": ("identification", "User identification name", False),

        # Authentication
        "token": ("authentication", "Rouge API token", False),

        # AWS
        "aws_access_key_id": ("aws", "AWS access key ID", False),
        "aws_secret_access_key": ("aws", "AWS secret access key", False),
        "aws_session_token": ("aws", "AWS session token", False),
        "aws_region": ("aws", "AWS region", False),

        # OpenTelemetry
        "otlp_endpoint": ("opentelemetry", "OTLP traces endpoint URL", False),
        "environment": ("opentelemetry", "Deployment environment (e.g., production, staging)", False),

        # Span Export
        "enable_span_console_export": ("export", "Enable console export of spans", False),
        "enable_log_console_export": ("export", "Enable console export of logs", False),
        "enable_span_cloud_export": ("export", "Enable cloud export of spans", False),
        "enable_log_cloud_export": ("export", "Enable cloud export of logs", False),

        # Mode
        "local_mode": ("mode", "Enable local development mode", False),

        # Endpoints
        "verification_endpoint": ("endpoints", "Credential verification endpoint", False),

        # Debugging
        "tracer_verbose": ("debugging", "Enable verbose tracer output", False),
        "logger_verbose": ("debugging", "Enable verbose logger output", False),

        # LLM Instrumentation
        "instrument_llm": ("llm", "Auto-instrument LLM providers", False),
        "llm_providers": ("llm", "List of LLM providers to instrument", False),

        # Security
        "allow_insecure_transport": ("security", "Allow HTTP endpoints (insecure)", False),
        "log_response_bodies": ("security", "Log HTTP response bodies", False),
        "log_request_bodies": ("security", "Log HTTP request bodies", False),
        "sanitize_telemetry_data": ("security", "Sanitize sensitive data in telemetry", False),

        # Dashboard
        "dashboard_username": ("dashboard", "Dashboard HTTP basic auth username", False),
        "dashboard_password": ("dashboard", "Dashboard HTTP basic auth password", False),
        "dashboard_path": ("dashboard", "Dashboard mount path", False),
    }

    for field_name, field_info in config_fields.items():
        category, description, required = field_categories.get(
            field_name,
            ("general", f"Configuration field: {field_name}", False)
        )

        env_var = env_var_reverse.get(field_name)

        registry.register_config_field(
            name=field_name,
            type_hint=str(field_info.type),
            default_value=field_info.default if field_info.default != inspect.Parameter.empty else None,
            description=description,
            required=required,
            category=category,
            env_var=env_var,
        )


def initialize_sdk_registry() -> None:
    """Initialize the SDK registry with all built-in functions and decorators.

    This function is called automatically when the introspection module is imported.
    """
    _register_sdk_functions()
    _register_decorators()
    _register_config_fields()


def get_all_decorators() -> Dict[str, Any]:
    """Get all registered decorators.

    Returns:
        Dictionary of decorator names to metadata
    """
    registry = get_registry()
    decorators = registry.get_all_decorators()

    return {
        name: {
            "name": meta.name,
            "docstring": meta.docstring,
            "options_schema": meta.options_schema,
            "examples": meta.examples,
            "category": meta.category,
        }
        for name, meta in decorators.items()
    }


def get_all_functions() -> Dict[str, Any]:
    """Get all registered SDK functions.

    Returns:
        Dictionary of function names to metadata
    """
    registry = get_registry()
    functions = registry.get_all_functions()

    return {
        name: {
            "name": meta.name,
            "module": meta.module,
            "qualname": meta.qualname,
            "signature": meta.signature,
            "docstring": meta.docstring,
            "parameters": meta.parameters,
            "return_type": meta.return_type,
            "is_async": meta.is_async,
            "category": meta.category,
            "examples": meta.examples,
            "tags": meta.tags,
        }
        for name, meta in functions.items()
    }


def get_config_schema() -> Dict[str, Any]:
    """Get the configuration schema.

    Returns:
        Dictionary describing all configuration fields
    """
    registry = get_registry()
    fields = registry.get_all_config_fields()

    # Group by category
    by_category: Dict[str, List[Dict[str, Any]]] = {}

    for name, meta in fields.items():
        if meta.category not in by_category:
            by_category[meta.category] = []

        by_category[meta.category].append({
            "name": meta.name,
            "type": meta.type_hint,
            "default": str(meta.default_value) if meta.default_value is not None else None,
            "description": meta.description,
            "required": meta.required,
            "env_var": meta.env_var,
        })

    return {
        "categories": by_category,
        "total_fields": len(fields),
    }


def get_examples() -> Dict[str, List[str]]:
    """Get usage examples organized by category.

    Returns:
        Dictionary of categories to example code snippets
    """
    examples = {
        "quickstart": [
            '''import rouge_ai

# Initialize Rouge
rouge_ai.init(service_name="my-app")

# Trace a function
@rouge_ai.trace()
def process_data(data):
    return data.upper()

# Use logging
logger = rouge_ai.get_logger(__name__)
logger.info("Processing started")''',
        ],
        "fastapi_integration": [
            '''import rouge_ai
from fastapi import FastAPI

app = FastAPI()

# Initialize and auto-trace all endpoints
rouge_ai.init(service_name="my-api")
rouge_ai.connect_fastapi(app)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id, "name": "John"}''',
        ],
        "dashboard": [
            '''import rouge_ai
from fastapi import FastAPI

app = FastAPI()

# Mount dashboard on your app at /rouge
rouge_ai.init(service_name="my-app")
rouge_ai.mount_dashboard(app, path="/rouge")

# Dashboard available at http://localhost:8000/rouge''',
        ],
        "advanced_tracing": [
            '''from rouge_ai import trace, TraceOptions, get_tracer

# Custom trace options
@trace(TraceOptions(
    span_name="fetch-user",
    trace_params=True,
    trace_return_value=True
))
async def fetch_user(user_id: int):
    return {"id": user_id}

# Manual span creation
tracer = get_tracer()
with tracer.start_as_current_span("custom-operation") as span:
    span.set_attribute("operation.type", "database_query")
    # Your code here''',
        ],
        "configuration": [
            '''import rouge_ai

# Full configuration
rouge_ai.init(
    service_name="my-app",
    environment="production",
    enable_span_console_export=True,
    enable_log_console_export=True,
    instrument_llm=True,
    llm_providers=["openai", "anthropic"],
    dashboard_username="admin",
    dashboard_password="secret"
)''',
        ],
    }

    return examples


def get_traced_functions() -> Dict[str, Any]:
    """Get all user's @trace decorated functions.

    Returns:
        Dictionary of function names to metadata
    """
    registry = get_registry()
    traced = registry.get_traced_functions()

    return {
        name: {
            "name": meta.name,
            "module": meta.module,
            "qualname": meta.qualname,
            "signature": meta.signature,
            "docstring": meta.docstring,
            "is_async": meta.is_async,
            "decorator_options": meta.decorator_options,
        }
        for name, meta in traced.items()
    }


# Auto-initialize when module is imported
initialize_sdk_registry()
