# Rouge Python SDK

<div align="center">
  <a href="https://rouge.ai/">
    <img src="https://raw.githubusercontent.com/rouge-ai/rouge/main/misc/images/rouge_logo.png" alt="Rouge Logo">
  </a>
</div>

Please see the [Python SDK Docs](https://docs.rouge.ai/sdk/python) for details.

## Installation

```bash
pip install rouge
```

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

Please reach out to founders@rouge.ai if you have any questions.

[company-website-url]: https://rouge.ai
[docs-image]: https://img.shields.io/badge/docs-rouge.ai-0dbf43
[docs-url]: https://docs.rouge.ai
[pypi-image]: https://badge.fury.io/py/rouge.svg
[pypi-sdk-downloads-image]: https://static.pepy.tech/badge/rouge
[pypi-sdk-downloads-url]: https://pypi.python.org/pypi/rouge
[pypi-url]: https://pypi.python.org/pypi/rouge
[testing-image]: https://github.com/rouge-ai/rouge/actions/workflows/test.yml/badge.svg
[testing-url]: https://github.com/rouge-ai/rouge/actions/workflows/test.yml
