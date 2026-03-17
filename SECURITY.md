# Security Policy

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
  - [How to Report](#how-to-report)
  - [What to Include](#what-to-include)
  - [Disclosure Timeline](#disclosure-timeline)
- [Security Best Practices](#security-best-practices-for-users)
  - [API Key Management](#api-key-management)
  - [Secrets Handling](#secrets-handling)
  - [Network Security](#network-security)
  - [Input Validation](#input-validation)
- [Security Features](#security-features)
- [Known Security Considerations](#known-security-considerations)
- [Security Advisories](#security-advisories)
- [Responsible Disclosure Policy](#responsible-disclosure-policy)
- [Contact](#contact)

---

## Supported Versions

The Rouge.AI team provides security updates for the following versions:

| Version | Supported          | Status      |
| ------- | ------------------ | ----------- |
| 0.0.x   | :white_check_mark: | Active      |
| < 0.0.1 | :x:                | Not Supported |

**Note**: We are committed to maintaining security updates for the current major version. As Rouge.AI matures, this table will be updated with our long-term support policy.

---

## Reporting a Vulnerability

The Rouge.AI team and community take all security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings and help us maintain a secure ecosystem for all users.

### How to Report

**Use GitHub's Private Vulnerability Reporting** (Preferred Method)

1. Navigate to the [Rouge.AI repository](https://github.com/revanthkumar96/rouge.ai-sdk)
2. Click on the **"Security"** tab
3. Select **"Report a vulnerability"**
4. Fill out the private vulnerability report form

**Do NOT**:
- ❌ Open public GitHub issues for security vulnerabilities
- ❌ Discuss vulnerabilities in public Discord channels
- ❌ Post about unpatched vulnerabilities on social media
- ❌ Exploit vulnerabilities beyond proof-of-concept testing

### What to Include

When reporting a vulnerability, please provide as much detail as possible:

#### Required Information

- **Clear description**: Explain the nature of the vulnerability and its potential impact
- **Steps to reproduce**: Detailed steps that allow us to reproduce the issue
  - Include specific commands, configurations, or code snippets
  - Provide sample data if relevant (sanitized of any sensitive information)
- **Affected versions**: Specify which version(s) of Rouge.AI are affected
- **Environment details**:
  - Python version
  - Operating system
  - LLM providers in use (if relevant)

#### Optional but Helpful

- **Proof of concept**: Non-destructive code demonstrating the vulnerability
- **Impact assessment**: Your evaluation of severity (Critical/High/Medium/Low)
- **Suggested fix**: If you have ideas for remediation
- **Your contact information**: Email address for follow-up communication

#### Example Report Template

```markdown
## Vulnerability Description
Brief summary of the security issue.

## Impact
What an attacker could accomplish by exploiting this vulnerability.

## Affected Versions
- Rouge.AI version: 0.0.1
- Python version: 3.11.5
- OS: Ubuntu 22.04

## Steps to Reproduce
1. Install Rouge.AI with: pip install rouge
2. Create a file `exploit.py` with the following code:
   [code here]
3. Run: python exploit.py
4. Observe: [what happens]

## Proof of Concept
[Sanitized code demonstrating the issue]

## Suggested Remediation
[Your ideas for fixing the issue, if any]

## Contact
Email: your-email@example.com
```

### Disclosure Timeline

**What to Expect After Reporting:**

| Timeframe | Action |
|-----------|--------|
| **48-72 hours** | Initial acknowledgment of your report |
| **1 week** | Initial assessment and severity classification |
| **2-4 weeks** | Regular updates on investigation progress |
| **Variable** | Patch development and testing (depends on severity) |
| **After patch** | Coordinated public disclosure and credit |

#### Severity Classifications

- **Critical**: Immediate exploitation possible; severe impact (RCE, data breach)
  - Target fix: 24-48 hours
- **High**: Exploitation likely; significant impact (auth bypass, privilege escalation)
  - Target fix: 1 week
- **Medium**: Exploitation possible with preconditions; moderate impact
  - Target fix: 2-4 weeks
- **Low**: Limited exploitation; minimal impact
  - Target fix: Next regular release

**We commit to**:
- Keep you informed throughout the process
- Work with you on disclosure timing
- Credit you in the security advisory (unless you prefer anonymity)
- Notify you before public disclosure

---

## Security Best Practices for Users

### API Key Management

**Protect your LLM provider API keys:**

```python
# ❌ Bad - Hardcoded API keys
import openai
openai.api_key = "sk-1234567890abcdef"  # Never do this!

# ✅ Good - Use environment variables
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
```

**Use a `.env` file with python-dotenv:**

```python
# .env file (add to .gitignore!)
OPENAI_API_KEY=sk-1234567890abcdef
ANTHROPIC_API_KEY=sk-ant-1234567890abcdef

# Python code
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env

api_key = os.environ.get("OPENAI_API_KEY")
```

**Never commit secrets to version control:**

```bash
# Add to .gitignore
.env
*.env
secrets.yaml
credentials.json
```

### Secrets Handling

**Rouge.AI Configuration:**

```python
import rouge
import os

# ✅ Good - No secrets in code
rouge.init(
    service_name="my-service",
    api_key=os.environ.get("ROUGE_API_KEY"),  # If applicable
)

# ❌ Bad - Hardcoded secrets
rouge.init(
    service_name="my-service",
    api_key="rouge-1234567890",  # Never hardcode!
)
```

### Network Security

**Use secure connections:**

```python
# Ensure HTTPS is used for external telemetry endpoints
rouge.init(
    service_name="my-service",
    exporter_endpoint="https://telemetry.example.com",  # HTTPS, not HTTP
)
```

**Validate SSL certificates in production:**

```python
import os

# Disable SSL verification only in development
VERIFY_SSL = os.environ.get("ENV") != "development"
```

### Input Validation

**Sanitize user input before logging:**

```python
import rouge
import re

logger = rouge.get_logger()

def process_user_input(user_input: str):
    # ❌ Bad - Logging raw user input (potential log injection)
    logger.info(f"Processing: {user_input}")

    # ✅ Good - Sanitize before logging
    sanitized = re.sub(r'[^\w\s-]', '', user_input)
    logger.info(f"Processing input", extra={
        "input_length": len(user_input),
        "sanitized_preview": sanitized[:50]
    })
```

**Validate data types:**

```python
from typing import Dict, Any

def configure_tracer(config: Dict[str, Any]):
    # ✅ Validate configuration keys
    allowed_keys = {"service_name", "sample_rate", "environment"}
    invalid_keys = set(config.keys()) - allowed_keys

    if invalid_keys:
        raise ValueError(f"Invalid config keys: {invalid_keys}")

    # ✅ Validate data types
    if not isinstance(config.get("sample_rate", 1.0), (int, float)):
        raise TypeError("sample_rate must be a number")
```

---

## Security Features

Rouge.AI implements several security features to protect your applications:

### 1. Local-First Architecture

By default, Rouge.AI processes telemetry data **locally**:
- No data sent to external servers without explicit configuration
- Full control over where and how data is exported
- Suitable for air-gapped environments

### 2. Minimal Permissions

Rouge.AI requires **no special permissions**:
- No filesystem access beyond standard Python operations
- No network access unless you configure exporters
- No elevated privileges required

### 3. Sanitized Logging

Sensitive data is automatically sanitized in logs:
- API keys are redacted in error messages
- Authentication headers are filtered
- PII detection and masking (configurable)

### 4. Dependency Security

We maintain security through:
- Regular dependency updates
- Automated vulnerability scanning
- Minimal dependency footprint
- Pinned dependency versions in releases

### 5. Open Source Transparency

As an open-source project:
- All code is publicly auditable
- Community can review security practices
- No hidden telemetry or tracking

---

## Known Security Considerations

### Data Retention

**Consideration**: When using exporters, telemetry data may be stored externally.

**Mitigation**:
- Configure data retention policies in your backend
- Use local exporters (file-based) for sensitive environments
- Implement data encryption at rest

### LLM Provider Credentials

**Consideration**: Rouge.AI instruments LLM provider SDKs that use API credentials.

**Mitigation**:
- Rouge.AI does **not** access, store, or transmit your API keys
- Follows provider SDK security practices
- Use environment variables for credential management

### Log Injection

**Consideration**: User-provided data in logs could lead to log injection attacks.

**Mitigation**:
- Sanitize user input before logging (see [Input Validation](#input-validation))
- Use structured logging with explicit fields
- Implement log analysis tools that detect injection attempts

### Third-Party Dependencies

**Consideration**: Dependencies may contain vulnerabilities.

**Mitigation**:
- We use Dependabot for automated security updates
- Regular security audits of dependencies
- Minimal dependency tree to reduce attack surface

---

## Security Advisories

**View published security advisories:**

👉 [GitHub Security Advisories](https://github.com/revanthkumar96/rouge.ai-sdk/security/advisories)

**Subscribe to security notifications:**

1. Watch the [Rouge.AI repository](https://github.com/revanthkumar96/rouge.ai-sdk)
2. Configure notifications for "Security alerts only"

---

## Responsible Disclosure Policy

We are committed to working with security researchers to verify, reproduce, and respond to legitimate vulnerability reports. We ask that you:

### Guidelines for Researchers

**Do**:
- ✅ Report vulnerabilities through private channels (GitHub Security)
- ✅ Allow reasonable time for us to respond and fix issues
- ✅ Make a good faith effort to avoid privacy violations and data destruction
- ✅ Only test against your own accounts/deployments

**Don't**:
- ❌ Access or modify other users' data
- ❌ Perform attacks that could harm availability (DoS, resource exhaustion)
- ❌ Exploit vulnerabilities beyond demonstrating proof-of-concept
- ❌ Publicly disclose vulnerabilities before they're patched

### Our Commitments

We commit to:
- ✅ Respond to your report within 72 hours
- ✅ Keep you updated on remediation progress
- ✅ Credit you in the security advisory (if desired)
- ✅ Not pursue legal action against researchers following this policy

### Safe Harbor

When conducting security research according to this policy, we consider your actions authorized and will not recommend or pursue legal action against you. If legal action is initiated by a third party, we will take steps to make it known that your actions were conducted in compliance with this policy.

---

## Contact

### Security Team

**Email**: [sudikondarevanthkumar@gmail.com](mailto:sudikondarevanthkumar@gmail.com)

**GitHub**: [Private Vulnerability Reporting](https://github.com/revanthkumar96/rouge.ai-sdk/security/advisories/new) (Preferred)

### Response Time

- **Critical vulnerabilities**: 24-48 hours
- **Other reports**: 48-72 hours

### PGP Key

For encrypted communications, please request our PGP key via email.

---

<div align="center">
  <p><strong>Thank you for helping keep Rouge.AI secure!</strong></p>
  <p>Your responsible disclosure helps protect the entire community. 🔒</p>
</div>
