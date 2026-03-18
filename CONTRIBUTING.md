# Contributing to Rouge.AI 🚀

Thank you for your interest in contributing to Rouge.AI! We're excited to have you join our community. As an open-source project in the rapidly evolving AI/ML observability space, we welcome contributions of all kinds—from bug fixes and features to documentation improvements and community support.

______________________________________________________________________

## Table of Contents

- [Join Our Community](#join-our-community)
  - [Communication Channels](#communication-channels)
  - [Schedule a Call](#schedule-a-call)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
  - [Verification Checklist](#verification-checklist)
- [Development Workflow](#development-workflow)
  - [Branch Naming](#branch-naming)
  - [Commit Messages](#commit-messages)
  - [Testing Your Changes](#testing-your-changes)
- [How to Contribute](#how-to-contribute)
  - [Reporting Issues](#reporting-issues)
  - [Contributing Code](#contributing-code)
  - [Contributing Documentation](#contributing-documentation)
- [Code Review Process](#code-review-process)
  - [Review Checklist](#review-checklist)
  - [Reviewer Responsibilities](#reviewer-responsibilities)
  - [Common Pitfalls](#common-pitfalls)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
  - [Writing Docstrings](#writing-docstrings)
  - [Examples](#examples)
- [Coding Principles](#coding-principles)
  - [Naming Conventions](#naming-conventions)
  - [Logging Guidelines](#logging-guidelines)
- [Style Guide](#style-guide)

______________________________________________________________________

## Join Our Community

### Communication Channels

**💬 Discord** (Primary)
Join our active community for real-time discussions, questions, and collaboration:
👉 [Join Discord](https://discord.gg/tPyffEZvvJ)

**🐛 GitHub Issues**
Report bugs, request features, or discuss technical topics:
👉 [GitHub Issues](https://github.com/revanthkumar96/rouge.ai-sdk/issues)

**📧 Email**
For private inquiries or security concerns:
👉 [sudikondarevanthkumar@gmail.com](mailto:sudikondarevanthkumar@gmail.com)

### Schedule a Call

Need to discuss a major contribution or architectural decision?
📅 [Schedule a 30-minute introduction call](https://cal.com/rouge/30min)

______________________________________________________________________

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** installed
- **Git** installed and configured
- **pip** package manager (comes with Python)
- A **GitHub account**
- Basic familiarity with Python and git workflows

### Environment Setup

Follow these steps to set up your development environment:

#### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/rouge.ai-sdk.git
cd rouge.ai-sdk
```

#### 2. Create a Virtual Environment

```bash
# Create a virtual environment
python3.11 -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install Rouge.AI with all development dependencies
pip install -e ".[all]"
```

This installs:

- Rouge.AI in editable mode
- All LLM provider packages
- Development tools (pytest, ruff, pre-commit, etc.)

#### 4. Set Up Pre-Commit Hooks

Pre-commit hooks automatically format and lint your code before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# (Optional) Run on all files to verify setup
pre-commit run --all-files
```

### Verification Checklist

Verify your setup is working correctly:

- [ ] Virtual environment is activated
- [ ] `python --version` shows Python 3.11+
- [ ] `pip show rouge-ai` displays package information
- [ ] `pre-commit run --all-files` completes without errors
- [ ] `pytest test` runs (even if some tests fail initially)

______________________________________________________________________

## Development Workflow

### Branch Naming

Use descriptive branch names that indicate the type of change:

```bash
# Feature branches
git checkout -b feature/add-gemini-support
git checkout -b feature/custom-span-attributes

# Bug fix branches
git checkout -b fix/openai-timeout-handling
git checkout -b fix/memory-leak-in-tracer

# Documentation branches
git checkout -b docs/improve-quickstart-guide
git checkout -b docs/add-api-examples
```

**Convention**: `type/short-description`

**Types**: `feature`, `fix`, `docs`, `refactor`, `test`, `chore`

### Commit Messages

Write clear, descriptive commit messages:

```bash
# Good examples
git commit -m "feat: add support for Anthropic Claude instrumentation"
git commit -m "fix: resolve race condition in async span creation"
git commit -m "docs: add examples for manual span creation"
git commit -m "test: add unit tests for LLM provider detection"

# Bad examples
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "WIP"
```

**Format**: `type: brief description`

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

### Testing Your Changes

Before submitting a pull request:

```bash
# Run all tests
pytest test

# Run specific test file
pytest test/test_llm_config.py

# Run with coverage
pytest test --cov=rouge_ai --cov-report=html

# Run pre-commit checks
pre-commit run --all-files

# Run on specific files
pre-commit run --files src/rouge_ai/tracer.py
```

______________________________________________________________________

## How to Contribute

### Reporting Issues

Found a bug or have a feature request? Here's how to report it effectively:

#### Bug Reports

Include the following information:

```markdown
**Description**: Brief description of the issue

**Steps to Reproduce**:
1. Step one
2. Step two
3. Step three

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- Rouge.AI version: [e.g., 0.0.7]
- Python version: [e.g., 3.11.5]
- OS: [e.g., Ubuntu 22.04]
- LLM provider: [e.g., OpenAI 1.12.0]

**Additional Context**: Any relevant logs or screenshots
```

#### Feature Requests

Describe:

- **The problem**: What pain point does this solve?
- **Proposed solution**: How would you like it to work?
- **Alternatives considered**: Other approaches you've thought about
- **Use case**: Specific scenarios where this would be valuable

### Contributing Code

We follow a standard fork-and-pull-request workflow:

#### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────┐
│  1. Fork & Clone     →    2. Create Branch                  │
│  3. Make Changes     →    4. Write Tests                    │
│  5. Run Tests        →    6. Commit Changes                 │
│  7. Push Branch      →    8. Create PR                      │
└─────────────────────────────────────────────────────────────┘
```

#### 1. Fork and Clone

Already covered in [Environment Setup](#environment-setup).

#### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

#### 3. Make Your Changes

- Write clean, readable code
- Follow our [Coding Principles](#coding-principles)
- Add docstrings to new functions/classes

#### 4. Write Tests

- Add unit tests for new features in the `test/` directory
- Ensure bug fixes include regression tests
- Aim for good test coverage (see [Testing Guidelines](#testing-guidelines))

#### 5. Run Tests and Linting

```bash
# Run tests
pytest test

# Run pre-commit checks
pre-commit run --all-files
```

#### 6. Commit Your Changes

```bash
git add .
git commit -m "feat: add support for new feature"
```

#### 7. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

#### 8. Create a Pull Request

- Go to the original repository on GitHub
- Click "New Pull Request"
- Select your branch
- Fill out the PR template with:
  - **Description**: What does this PR do?
  - **Related Issues**: Link any relevant issues
  - **Testing**: How did you test this?
  - **Screenshots**: If applicable

#### What to Include in Your PR

✅ **Do Include**:

- Relevant unit tests for new features
- Documentation updates if behavior changes
- Clear commit messages
- Screenshots/examples for UI changes

❌ **Don't Include**:

- Unrelated changes (create separate PRs)
- Large refactors mixed with features
- Commented-out code
- Temporary debugging code

### Contributing Documentation

Documentation improvements are highly valued! You can contribute:

- **README improvements**: Clarify confusing sections
- **API documentation**: Add examples or explanations
- **Tutorials**: Create guides for common use cases
- **Docstring improvements**: Enhance code documentation

Documentation changes follow the same PR process as code changes.

______________________________________________________________________

## Code Review Process

All pull requests undergo code review to maintain quality and consistency.

### Purpose of Code Reviews

1. **Maintain Code Quality**: Keep the codebase clean, readable, and maintainable
1. **Knowledge Sharing**: Help contributors learn best practices
1. **Bug Prevention**: Catch issues before they reach production
1. **Consistency**: Ensure uniform style and architecture

### Review Process Overview

```
┌───────────────────────────────────────────────────────┐
│  PR Submitted  →  Automated Checks  →  Review         │
│  Feedback      →  Changes Made      →  Re-review      │
│  Approval      →  Merge                               │
└───────────────────────────────────────────────────────┘
```

1. **PR Submitted**: Author creates pull request
1. **Automated Checks**: CI runs tests, linting, etc.
1. **Review**: Reviewers examine code and provide feedback
1. **Changes**: Author addresses feedback
1. **Re-review**: Reviewers verify changes
1. **Approval**: At least two reviewers approve
1. **Merge**: Maintainer merges to main branch

### Review Checklist

Reviewers evaluate PRs based on these criteria:

#### Functionality

- [ ] Code performs the intended task correctly
- [ ] Edge cases are handled appropriately
- [ ] No obvious bugs or logical errors

#### Testing

- [ ] Sufficient test coverage for new code
- [ ] All tests pass in CI
- [ ] Tests are clear and maintainable

#### Security

- [ ] No security vulnerabilities introduced
- [ ] Input validation where appropriate
- [ ] Secrets not hardcoded

#### Code Quality

- [ ] Code is readable and well-structured
- [ ] Comments explain "why", not "what"
- [ ] No unnecessary complexity

#### Style & Standards

- [ ] Follows project coding standards
- [ ] Ruff formatting checks pass
- [ ] Docstrings follow Google style guide

#### Design

- [ ] Consistent with existing architecture
- [ ] No unnecessary code duplication
- [ ] Dependencies are appropriate

### Reviewer Responsibilities

**As a reviewer, you should**:

- ✅ Review PRs promptly (within 48 hours when possible)
- ✅ Provide clear, constructive feedback
- ✅ Explain the reasoning behind requested changes
- ✅ Acknowledge good work and improvements
- ✅ Be respectful and professional
- ✅ Test the changes locally if needed

**Avoid**:

- ❌ Nitpicking minor style issues (let automated tools handle this)
- ❌ Requesting changes without explanation
- ❌ Blocking PRs for personal preferences
- ❌ Rushing reviews without thorough examination

### Common Pitfalls

#### For Contributors

**❌ Large Pull Requests**

- Problem: PRs with 1000+ line changes are hard to review
- Solution: Break changes into smaller, focused PRs

**❌ Ignoring Feedback**

- Problem: Not addressing reviewer comments
- Solution: Respond to all feedback—agree, discuss, or explain

**❌ Mixing Concerns**

- Problem: Combining feature + refactor + bug fix in one PR
- Solution: Create separate PRs for each concern

#### For Reviewers

**❌ Rushed Reviews**

- Problem: Missing bugs or design issues
- Solution: Take time to thoroughly understand changes

**❌ Bikeshedding**

- Problem: Endless debate over trivial details
- Solution: Focus on significant issues; use automated tools for style

______________________________________________________________________

## Testing Guidelines

Quality tests are essential for maintaining Rouge.AI's reliability.

### When to Write Tests

**Always write tests when**:

- ✅ Adding new features or functionality
- ✅ Fixing bugs (write a regression test first)
- ✅ Refactoring existing code

### Test Structure

```python
# test/test_feature.py
import pytest
from rouge_ai import TraceOptions

class TestSomeFeature:
    """Test suite for SomeFeature functionality."""

    def test_basic_functionality(self):
        """Test that basic feature works as expected."""
        config = TraceOptions()
        # ... test logic

    def test_edge_case_empty_input(self):
        """Test handling of empty input."""
        # ... test logic

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async functionality."""
        # ... test logic
```

### Test Organization

Place tests in the `test/` directory:

```
test/
├── test_core.py           # Core functionality tests
├── test_llm_config.py     # LLM configuration tests
├── test_tracing.py        # Tracing functionality tests
└── test_providers/        # Provider-specific tests
    ├── test_openai.py
    └── test_anthropic.py
```

### Running Tests

```bash
# Run all tests
pytest test

# Run specific test file
pytest test/test_llm_config.py

# Run specific test
pytest test/test_llm_config.py::test_provider_detection

# Run with coverage report
pytest test --cov=rouge_ai --cov-report=html

# Run only failed tests from last run
pytest --lf
```

______________________________________________________________________

## Documentation Standards

### Writing Docstrings

We follow the **Google Python Style Guide** for docstrings.

#### Basic Structure

```python
def function_name(param1: str, param2: int = 0) -> bool:
    r"""Brief one-line description of what the function does.

    More detailed explanation if needed. This can span multiple lines
    and should explain the purpose, behavior, and any important details
    about the function.

    Args:
        param1: Description of param1. Keep under 79 characters per
            line. Indent continuation lines by 4 spaces.
        param2: Description of param2. Use (default: :obj:`value`) to
            indicate default values. (default: :obj:`0`)

    Returns:
        Description of return value. Explain what the function returns
        and under what conditions.

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is not an integer.

    Example:
        Basic usage example::

            result = function_name("example", param2=5)
            print(result)  # True
    """
    pass
```

#### Key Rules

1. **Use raw docstrings**: Start with `r"""`
1. **79 character limit**: Keep lines under 79 characters
1. **No line break after opening**: Start summary on same line as `r"""`
1. **Type annotations**: Include types in function signature AND docstring
1. **Default values**: Use `(default: :obj:`value`)` notation

### Examples

#### Class Docstring

```python
class TraceConfig:
    r"""Configuration for distributed tracing.

    This class manages tracing configuration including sampling rates,
    span attributes, and export settings. It provides a fluent interface
    for building complex configurations.

    Args:
        service_name: The name of the service being traced. Used to
            identify traces in the backend. (default: :obj:`"unknown"`)
        sample_rate: Sampling rate between 0.0 and 1.0. Controls what
            percentage of traces are collected. (default: :obj:`1.0`)
        enable_metrics: Whether to collect metrics alongside traces.
            (default: :obj:`True`)

    Attributes:
        service_name: The configured service name.
        sample_rate: The configured sampling rate.

    Example:
        Creating a basic configuration::

            config = TraceConfig(
                service_name="my-service",
                sample_rate=0.5
            )

        Using the fluent interface::

            config = TraceConfig("my-service") \\
                .with_sample_rate(0.5) \\
                .with_metrics(True)
    """
    pass
```

#### Method Docstring

```python
def start_span(self, name: str, attributes: dict = None) -> Span:
    r"""Start a new tracing span.

    Creates and returns a new span with the given name and optional
    attributes. The span must be explicitly ended by calling end() or
    used as a context manager.

    Args:
        name: The name of the span. Should be descriptive and follow
            the format "component.operation" (e.g., "db.query").
        attributes: Optional dictionary of key-value pairs to attach
            to the span. Keys must be strings. (default: :obj:`None`)

    Returns:
        A Span object that can be used as a context manager or ended
        manually.

    Raises:
        ValueError: If name is empty or None.
        TypeError: If attributes contains non-string keys.

    Example:
        Using as a context manager::

            with tracer.start_span("api.request") as span:
                span.set_attribute("http.method", "GET")
                result = make_request()

        Manual span management::

            span = tracer.start_span("processing")
            try:
                process_data()
            finally:
                span.end()
    """
    pass
```

______________________________________________________________________

## Coding Principles

### Naming Conventions

**❌ Avoid Abbreviations**

Abbreviations reduce code clarity, especially when AI agents read your code.

```python
# Bad - unclear abbreviations
msg_win_sz = 100
usr_cfg = get_config()
tmp_buf = []

# Good - clear, descriptive names
message_window_size = 100
user_configuration = get_config()
temporary_buffer = []
```

**✅ Use Descriptive Names**

```python
# Bad
def proc_data(d):
    res = []
    for x in d:
        res.append(x * 2)
    return res

# Good
def process_user_scores(scores: list[int]) -> list[int]:
    """Double each score in the list."""
    doubled_scores = []
    for score in scores:
        doubled_scores.append(score * 2)
    return doubled_scores
```

### Logging Guidelines

**❌ Never Use `print()`**

Always use Python's `logging` module for output.

```python
# Bad - using print
def process_request(user_id: str):
    print("Processing request")
    print(f"User ID: {user_id}")
    result = do_processing()
    print(f"Result: {result}")
    return result

# Good - using logger
import logging
logger = logging.getLogger(__name__)

def process_request(user_id: str):
    logger.info("Processing request")
    logger.debug(f"User ID: {user_id}")
    result = do_processing()
    logger.info(f"Request processed successfully", extra={
        "user_id": user_id,
        "result_count": len(result)
    })
    return result
```

**Log Levels**:

- `logger.debug()`: Detailed diagnostic information
- `logger.info()`: General informational messages
- `logger.warning()`: Warning messages for potentially harmful situations
- `logger.error()`: Error messages for failures
- `logger.critical()`: Critical failures requiring immediate attention

______________________________________________________________________

## Style Guide

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting and linting, following the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).

### Automatic Formatting

Pre-commit hooks automatically format your code:

```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files src/rouge_ai/tracer.py test/tracer/test_tracer.py
```

### Key Style Points

- **Line length**: Maximum 79 characters (docstrings and comments), 88 for code
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Prefer double quotes `"` for strings
- **Imports**: Group in order: standard library, third-party, local
- **Type hints**: Use type annotations for function signatures

### Import Organization

```python
# Standard library imports
import logging
import sys
from typing import Optional, Dict, Any

# Third-party imports
import pytest
from opentelemetry import trace

# Local application imports
from rouge_ai.tracer import TraceOptions
from rouge_ai.config import RougeConfig
```

______________________________________________________________________

## Questions?

If you have questions not covered in this guide:

1. Check existing [GitHub Issues](https://github.com/revanthkumar96/rouge.ai-sdk/issues)
1. Ask on [Discord](https://discord.gg/tPyffEZvvJ)
1. Email us at [sudikondarevanthkumar@gmail.com](mailto:sudikondarevanthkumar@gmail.com)

______________________________________________________________________

<div align="center">
  <p><strong>Thank you for contributing to Rouge.AI!</strong></p>
  <p>Your contributions help make AI observability better for everyone. 🎉</p>
</div>
