# Rouge Python SDK

<div align="center">
  <a href="https://github.com/revanthkumar96/rouge.ai-sdk">
    <img src="https://raw.githubusercontent.com/revanthkumar96/rouge.ai-sdk/main/misc/images/rouge_logo.png" alt="Rouge Logo">
  </a>
</div>

Please see the [Python SDK Docs](https://github.com/revanthkumar96/rouge.ai-sdk) for details.

## Installation

```bash
pip install rouge
# Or with LLM auto-instrumentation support:
pip install "rouge[llm]"
```

Then initialize:

```python
import rouge

# Basic initialization (auto-detects and instruments all installed LLM providers)
rouge.init(
    service_name="my-llm-service",
    # ... other config ...
)

# Advanced LLM configuration
rouge.init(
    service_name="my-llm-service",
    instrument_llm=True,                # Enable/disable all LLM instrumentation
    llm_providers=["openai", "anthropic"] # Only instrument specific providers
)
```

Supported LLM providers and frameworks: OpenAI, Anthropic, Cohere, Mistral AI, Vertex AI, AWS Bedrock, Replicate, Google Generative AI (Gemini), LangChain, LlamaIndex.

## Examples

```python
import rouge
import asyncio

logger = rouge.get_logger()

@rouge.trace()
async def greet(name: str) -> str:
    logger.info(f"Greeting inside traced function: {name}")
    # Simulate some async work
    await asyncio.sleep(0.1)
    return f"Hello, {name}!"

async def main():
    result = await greet("world")
    logger.info(f"Greeting result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Contact Us

Please reach out to sudikondarevanthkumar@gmail.com if you have any questions.
