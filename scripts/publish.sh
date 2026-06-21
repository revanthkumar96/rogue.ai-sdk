#!/usr/bin/env bash
# Publish the built rouge-ai distribution to PyPI.
#
# Reads PYPI_TOKEN from the repo-root .env at runtime (the token is never
# printed). Build first with `python -m build`, then run this script.
#
# Usage:
#   bash scripts/publish.sh            # upload dist/* to PyPI
#   REPOSITORY=testpypi bash scripts/publish.sh   # upload to TestPyPI
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "ERROR: .env not found at repo root (expected PYPI_TOKEN=...)." >&2
  exit 1
fi

if ! ls dist/*.whl >/dev/null 2>&1; then
  echo "ERROR: no artifacts in dist/. Run 'python -m build' first." >&2
  exit 1
fi

# Load .env without echoing any values.
set -a
# shellcheck disable=SC1091
source .env
set +a

if [ -z "${PYPI_TOKEN:-}" ]; then
  echo "ERROR: PYPI_TOKEN is not set in .env." >&2
  exit 1
fi

echo "Validating artifacts..."
python -m twine check dist/*

echo "Uploading dist/* to ${REPOSITORY:-pypi}..."
TWINE_USERNAME=__token__ \
TWINE_PASSWORD="$PYPI_TOKEN" \
python -m twine upload ${REPOSITORY:+--repository "$REPOSITORY"} dist/*

echo "Done."
