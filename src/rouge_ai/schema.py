"""Schema generation for Rouge.ai SDK.

This module generates OpenAPI-like JSON schemas describing the Rouge.ai SDK's
capabilities, functions, decorators, and configuration options.
"""

from typing import Any, Dict

from rouge_ai.introspection import (
    get_all_decorators,
    get_all_functions,
    get_config_schema,
    get_examples,
    get_traced_functions,
)


def generate_sdk_schema() -> Dict[str, Any]:
    """Generate a complete schema describing the Rouge.ai SDK.

    This schema includes all public functions, decorators, configuration options,
    and usage examples in a structured format similar to OpenAPI.

    Returns:
        Dictionary containing the full SDK schema
    """
    schema = {
        "sdk": {
            "name": "rouge-ai",
            "version": _get_version(),
            "description": "Production-ready observability SDK for LLM applications",
        },
        "functions": get_all_functions(),
        "decorators": get_all_decorators(),
        "config": get_config_schema(),
        "examples": get_examples(),
        "traced_functions": get_traced_functions(),
        "endpoints": {
            "dashboard": {
                "standalone": {
                    "method": "launch_dashboard",
                    "url_pattern": "http://{host}:{port}",
                    "default_port": 10108,
                    "description": "Standalone dashboard on separate port",
                },
                "mounted": {
                    "method": "mount_dashboard",
                    "url_pattern": "http://{host}:{port}{path}",
                    "default_path": "/rouge",
                    "description": "Dashboard mounted on existing FastAPI app",
                },
            },
        },
        "integrations": {
            "fastapi": {
                "method": "connect_fastapi",
                "description": "Auto-trace all FastAPI endpoints",
                "auto_mount_dashboard": True,
            },
        },
    }

    return schema


def generate_decorator_schema(decorator_name: str) -> Dict[str, Any]:
    """Generate schema for a specific decorator.

    Args:
        decorator_name: Name of the decorator (e.g., 'trace')

    Returns:
        Dictionary with decorator schema, or None if not found
    """
    decorators = get_all_decorators()

    if decorator_name not in decorators:
        return {}

    return decorators[decorator_name]


def generate_function_schema(function_name: str) -> Dict[str, Any]:
    """Generate schema for a specific function.

    Args:
        function_name: Fully qualified function name

    Returns:
        Dictionary with function schema, or None if not found
    """
    functions = get_all_functions()

    if function_name not in functions:
        return {}

    return functions[function_name]


def generate_config_schema_formatted() -> Dict[str, Any]:
    """Generate a formatted configuration schema with examples.

    Returns:
        Dictionary with formatted config schema
    """
    config = get_config_schema()

    # Add usage examples for each category
    category_examples = {
        "identification": {
            "service_name": "my-app",
            "github_owner": "myorg",
            "github_repo_name": "myrepo",
        },
        "aws": {
            "aws_region": "us-west-2",
        },
        "opentelemetry": {
            "otlp_endpoint": "https://localhost:4318/v1/traces",
            "environment": "production",
        },
        "export": {
            "enable_span_console_export": True,
            "enable_log_console_export": True,
        },
        "llm": {
            "instrument_llm": True,
            "llm_providers": ["openai", "anthropic"],
        },
        "dashboard": {
            "dashboard_username": "admin",
            "dashboard_password": "secret",
            "dashboard_path": "/rouge",
        },
    }

    # Add examples to categories
    for category, fields in config.get("categories", {}).items():
        if category in category_examples:
            config["categories"][category] = {
                "fields": fields,
                "example": category_examples[category],
            }
        else:
            config["categories"][category] = {
                "fields": fields,
            }

    return config


def generate_quick_reference() -> Dict[str, Any]:
    """Generate a quick reference guide for the SDK.

    Returns:
        Dictionary with quick reference information
    """
    return {
        "installation": {
            "pip": "pip install rouge-ai",
        },
        "quickstart": {
            "steps": [
                {
                    "step": 1,
                    "title": "Initialize Rouge",
                    "code": 'import rouge_ai\n\nrouge_ai.init(service_name="my-app")',
                },
                {
                    "step": 2,
                    "title": "Trace your functions",
                    "code": '@rouge_ai.trace()\ndef my_function():\n    return "Hello!"',
                },
                {
                    "step": 3,
                    "title": "Launch dashboard",
                    "code": 'rouge_ai.launch_dashboard()',
                },
            ],
        },
        "common_patterns": {
            "fastapi_integration": {
                "description": "Auto-trace all FastAPI endpoints",
                "code": '''from fastapi import FastAPI\nimport rouge_ai\n\napp = FastAPI()\nrouge_ai.init(service_name="my-api")\nrouge_ai.connect_fastapi(app)''',
            },
            "custom_tracing": {
                "description": "Trace with custom options",
                "code": '''from rouge_ai import trace, TraceOptions\n\n@trace(TraceOptions(trace_params=True, trace_return_value=True))\ndef process(data):\n    return data''',
            },
            "logging": {
                "description": "Use structured logging",
                "code": '''logger = rouge_ai.get_logger(__name__)\nlogger.info("Event occurred", extra={"user_id": 123})''',
            },
        },
        "dashboard_access": {
            "standalone": "http://localhost:10108",
            "mounted": "http://localhost:8000/rouge",
        },
    }


def _get_version() -> str:
    """Get the current SDK version.

    Returns:
        Version string
    """
    try:
        from rouge_ai import __version__
        return __version__
    except ImportError:
        return "unknown"


def export_schema_as_json() -> str:
    """Export the full SDK schema as JSON string.

    Returns:
        JSON string representation of the schema
    """
    import json
    schema = generate_sdk_schema()
    return json.dumps(schema, indent=2)


def export_schema_as_markdown() -> str:
    """Export the SDK schema as Markdown documentation.

    Returns:
        Markdown string representation of the schema
    """
    schema = generate_sdk_schema()
    functions = schema.get("functions", {})
    decorators = schema.get("decorators", {})
    config = schema.get("config", {})

    md = []
    md.append(f"# Rouge.ai SDK Reference (v{schema['sdk']['version']})")
    md.append("")
    md.append(schema['sdk']['description'])
    md.append("")

    # Decorators
    md.append("## Decorators")
    md.append("")
    for name, dec in decorators.items():
        md.append(f"### @{name}")
        if dec.get("docstring"):
            md.append(dec["docstring"])
        md.append("")
        if dec.get("examples"):
            md.append("**Examples:**")
            for example in dec["examples"]:
                md.append("```python")
                md.append(example)
                md.append("```")
                md.append("")

    # Functions by category
    md.append("## Functions")
    md.append("")

    # Group functions by category
    by_category: Dict[str, list] = {}
    for name, func in functions.items():
        category = func.get("category", "general")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append((name, func))

    for category, funcs in sorted(by_category.items()):
        md.append(f"### {category.title()}")
        md.append("")

        for name, func in funcs:
            md.append(f"#### `{func['qualname']}{func['signature']}`")
            if func.get("docstring"):
                md.append(func["docstring"])
            md.append("")

            if func.get("examples"):
                md.append("**Examples:**")
                for example in func["examples"]:
                    md.append("```python")
                    md.append(example)
                    md.append("```")
                    md.append("")

    # Configuration
    md.append("## Configuration")
    md.append("")
    categories = config.get("categories", {})
    for category, fields in sorted(categories.items()):
        md.append(f"### {category.title()}")
        md.append("")
        md.append("| Field | Type | Default | Description |")
        md.append("|-------|------|---------|-------------|")

        for field in fields:
            name = field.get("name", "")
            type_hint = field.get("type", "")
            default = field.get("default", "None")
            description = field.get("description", "")
            md.append(f"| `{name}` | `{type_hint}` | `{default}` | {description} |")

        md.append("")

    return "\n".join(md)
