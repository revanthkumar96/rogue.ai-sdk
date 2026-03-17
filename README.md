# Rouge.AI Python SDK

<div align="center">
  <a href="https://github.com/revanthkumar96/rouge.ai-sdk">
    <img src="https://raw.githubusercontent.com/revanthkumar96/rouge.ai-sdk/main/misc/images/rouge_logo.png" alt="Rouge Logo">
  </a>

  <p><strong>Production-ready observability and instrumentation for LLM applications</strong></p>

  [![PyPI version](https://badge.fury.io/py/rouge.svg)](https://badge.fury.io/py/rouge)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![License](https://img.shields.io/github/license/revanthkumar96/rouge.ai-sdk)](https://github.com/revanthkumar96/rouge.ai-sdk/blob/main/LICENSE)
</div>

---

## Table of Contents

- [About](#about)
- [Key Features](#key-features)
- [Installation](#installation)
  - [Basic Installation](#basic-installation)
  - [With LLM Support](#with-llm-support)
  - [Verifying Installation](#verifying-installation)
- [Quick Start](#quick-start)
  - [Basic Usage](#basic-usage)
  - [Async Functions](#async-functions)
  - [LLM Auto-Instrumentation](#llm-auto-instrumentation)
- [Configuration](#configuration)
  - [Basic Configuration](#basic-configuration)
  - [Advanced LLM Configuration](#advanced-llm-configuration)
  - [Configuration Options](#configuration-options)
- [LLM Provider Support](#llm-provider-support)
- [Examples](#examples)
  - [Tracing Decorators](#tracing-decorators)
  - [Manual Spans](#manual-spans)
  - [Logging Integration](#logging-integration)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Support](#support)

---

## About

**Rouge.AI** is a powerful Python SDK designed to provide comprehensive observability, tracing, and monitoring for LLM (Large Language Model) applications. It automatically instruments popular LLM providers and frameworks, giving you deep insights into your AI application's performance, costs, and behavior.

Whether you're building chatbots, AI assistants, or complex multi-agent systems, Rouge.AI helps you:
- Monitor LLM API calls and performance metrics
- Track costs and token usage across providers
- Debug production issues with detailed traces
- Optimize latency and throughput
- Ensure reliability with comprehensive logging

---

## Key Features

- **🔌 Auto-Instrumentation**: Automatic instrumentation for 10+ LLM providers and frameworks
- **📊 Distributed Tracing**: Full request tracing with context propagation
- **📝 Structured Logging**: Production-ready logging with configurable levels
- **⚡ Async Support**: Native support for asyncio and concurrent operations
- **🎯 Zero-Config Start**: Works out-of-the-box with sensible defaults
- **🔧 Highly Configurable**: Fine-grained control over instrumentation behavior
- **🪶 Lightweight**: Minimal performance overhead
- **🔒 Secure**: No data sent externally without explicit configuration

---

## Installation

### Basic Installation

Install Rouge.AI using pip:

```bash
pip install rouge
```

### With LLM Support

For automatic LLM provider instrumentation, install with the `llm` extra:

```bash
pip install "rouge[llm]"
```

This includes instrumentation packages for all supported providers.

### Verifying Installation

After installation, verify that Rouge.AI is correctly installed:

```python
import rouge
print(rouge.__version__)
```

---

## Quick Start

### Basic Usage

Initialize Rouge.AI in your application:

```python
import rouge

# Initialize with minimal configuration
rouge.init(service_name="my-app")

# Get a logger instance
logger = rouge.get_logger()

logger.info("Application started successfully")
```

### Async Functions

Rouge.AI fully supports async/await patterns:

```python
import rouge
import asyncio

logger = rouge.get_logger()

@rouge.trace()
async def greet(name: str) -> str:
    logger.info(f"Greeting user: {name}")
    await asyncio.sleep(0.1)  # Simulate async work
    return f"Hello, {name}!"

async def main():
    result = await greet("world")
    logger.info(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### LLM Auto-Instrumentation

Rouge.AI automatically detects and instruments installed LLM providers:

```python
import rouge
from openai import OpenAI

# Initialize Rouge.AI - automatically instruments OpenAI
rouge.init(
    service_name="my-llm-service",
    instrument_llm=True
)

# Your OpenAI calls are now automatically traced
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

---

## Configuration

### Basic Configuration

```python
import rouge

rouge.init(
    service_name="my-service",      # Required: Your service identifier
    environment="production",        # Optional: deployment environment
    version="1.0.0",                # Optional: service version
)
```

### Advanced LLM Configuration

```python
import rouge

rouge.init(
    service_name="my-llm-service",

    # LLM instrumentation controls
    instrument_llm=True,                      # Enable/disable all LLM instrumentation
    llm_providers=["openai", "anthropic"],    # Only instrument specific providers

    # Additional configuration
    environment="staging",
    version="2.1.0",
)
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_name` | `str` | **Required** | Unique identifier for your service |
| `environment` | `str` | `None` | Deployment environment (e.g., "production", "staging") |
| `version` | `str` | `None` | Service version for tracking |
| `instrument_llm` | `bool` | `True` | Enable automatic LLM provider instrumentation |
| `llm_providers` | `List[str]` | `None` | Specific providers to instrument (default: all detected) |

---

## LLM Provider Support

Rouge.AI automatically instruments the following LLM providers and frameworks:

| Provider/Framework | Status | Package Required |
|-------------------|--------|------------------|
| **OpenAI** | ✅ Supported | `openai` |
| **Anthropic** | ✅ Supported | `anthropic` |
| **Cohere** | ✅ Supported | `cohere` |
| **Mistral AI** | ✅ Supported | `mistralai` |
| **Google Vertex AI** | ✅ Supported | `google-cloud-aiplatform` |
| **AWS Bedrock** | ✅ Supported | `boto3` |
| **Replicate** | ✅ Supported | `replicate` |
| **Google Generative AI (Gemini)** | ✅ Supported | `google-generativeai` |
| **LangChain** | ✅ Supported | `langchain` |
| **LlamaIndex** | ✅ Supported | `llama-index` |

**Note**: Only installed providers will be instrumented. Rouge.AI automatically detects available packages.

---

## Examples

### Tracing Decorators

Use the `@rouge.trace()` decorator to automatically trace function execution:

```python
import rouge

rouge.init(service_name="example-service")
logger = rouge.get_logger()

@rouge.trace()
def process_data(data: dict) -> dict:
    logger.info(f"Processing {len(data)} items")
    # Your processing logic here
    return {"status": "processed", "count": len(data)}

result = process_data({"items": [1, 2, 3]})
```

### Manual Spans

For fine-grained control, create manual spans:

```python
import rouge

rouge.init(service_name="manual-tracing")
tracer = rouge.get_tracer()

with tracer.start_span("database_query") as span:
    span.set_attribute("query.type", "SELECT")
    span.set_attribute("query.table", "users")
    # Execute your database query
    result = execute_query("SELECT * FROM users")
    span.set_attribute("result.count", len(result))
```

### Logging Integration

Rouge.AI provides structured logging with automatic trace correlation:

```python
import rouge

rouge.init(service_name="logging-example")
logger = rouge.get_logger()

@rouge.trace()
def user_signup(email: str, username: str):
    logger.info(f"New user signup attempt", extra={
        "email": email,
        "username": username
    })

    try:
        # Signup logic
        create_user(email, username)
        logger.info("User created successfully")
    except Exception as e:
        logger.error(f"Signup failed: {str(e)}", exc_info=True)
        raise
```

---

## API Reference

### Core Functions

#### `rouge.init(**config)`
Initialize the Rouge.AI SDK with configuration options.

**Parameters:**
- `service_name` (str, required): Service identifier
- `environment` (str, optional): Deployment environment
- `version` (str, optional): Service version
- `instrument_llm` (bool, optional): Enable LLM instrumentation (default: True)
- `llm_providers` (List[str], optional): Specific providers to instrument

#### `rouge.get_logger(name: str = None)`
Get a logger instance for structured logging.

**Returns:** Logger instance with trace context integration

#### `rouge.get_tracer(name: str = None)`
Get a tracer instance for manual span creation.

**Returns:** Tracer instance for creating spans

#### `@rouge.trace(name: str = None, **attributes)`
Decorator to automatically trace function execution.

**Parameters:**
- `name` (str, optional): Custom span name (defaults to function name)
- `**attributes`: Additional span attributes

For complete API documentation, see the [Python SDK Documentation](https://github.com/revanthkumar96/rouge.ai-sdk).

---

## Troubleshooting

### LLM Provider Not Instrumented

**Problem**: LLM calls are not being traced.

**Solution**:
1. Ensure you installed Rouge.AI with LLM support: `pip install "rouge[llm]"`
2. Verify the provider package is installed (e.g., `pip install openai`)
3. Check that `instrument_llm=True` in your `rouge.init()` call
4. Ensure `rouge.init()` is called before importing the LLM provider

### Import Errors

**Problem**: `ModuleNotFoundError` when importing Rouge.AI.

**Solution**:
1. Verify installation: `pip show rouge`
2. Check Python version compatibility (requires Python 3.11+)
3. Ensure you're using the correct virtual environment

### Performance Issues

**Problem**: Application slowdown after adding instrumentation.

**Solution**:
1. Reduce logging verbosity in production
2. Use sampling for high-throughput applications
3. Disable instrumentation for specific providers if not needed
4. Contact support if issues persist

---

## FAQ

### Q: Does Rouge.AI send data to external servers?

**A**: No. By default, Rouge.AI only processes data locally. You have full control over where telemetry data is sent.

### Q: What's the performance impact?

**A**: Rouge.AI is designed for production use with minimal overhead (typically <1% latency increase). Exact impact depends on your instrumentation configuration.

### Q: Can I use Rouge.AI with multiple LLM providers?

**A**: Yes! Rouge.AI automatically instruments all detected providers. You can also selectively enable specific providers using the `llm_providers` parameter.

### Q: Is Rouge.AI compatible with serverless environments?

**A**: Yes. Rouge.AI works in serverless environments (AWS Lambda, Google Cloud Functions, etc.). Initialization time is minimal.

### Q: How do I disable instrumentation for a specific function?

**A**: Simply don't use the `@rouge.trace()` decorator on that function. Instrumentation is opt-in at the function level.

### Q: Can I use Rouge.AI in Jupyter notebooks?

**A**: Yes. Rouge.AI works seamlessly in Jupyter notebooks and other interactive environments.

---

## Contributing

We welcome contributions from the community! Whether you want to:
- Report bugs or request features
- Improve documentation
- Submit code changes
- Add support for new LLM providers

Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

**Quick Links:**
- [Code of Conduct](CONTRIBUTING.md#join-our-community)
- [Development Setup](CONTRIBUTING.md#getting-started)
- [Pull Request Process](CONTRIBUTING.md#contributing-code)

---

## Security

Security is a top priority for Rouge.AI. We take all security vulnerabilities seriously.

**To report a security vulnerability:**
- Use GitHub's [Private Vulnerability Reporting](https://github.com/revanthkumar96/rouge.ai-sdk/security/advisories/new)
- **Do not** open public issues for security concerns

For more details, see our [Security Policy](SECURITY.md).

---

## License

This project is licensed under the [MIT License](LICENSE). See the LICENSE file for details.

---

## Support

Need help? We're here for you!

### 📧 Email
[sudikondarevanthkumar@gmail.com](mailto:sudikondarevanthkumar@gmail.com)

### 💬 Discord
Join our community: [Discord Server](https://discord.gg/tPyffEZvvJ)

### 🐛 Issues
Report bugs or request features: [GitHub Issues](https://github.com/revanthkumar96/rouge.ai-sdk/issues)

### 📅 Schedule a Call
Need dedicated support? [Book a 30-minute call](https://cal.com/rouge/30min)

---

<div align="center">
  <p>Made with ❤️ by the Rouge.AI team</p>
  <p>⭐ Star us on GitHub if Rouge.AI helps your project!</p>
</div>
