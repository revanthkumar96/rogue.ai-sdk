# Rouge.ai Dashboard

A web UI for observing your LLM application: real-time telemetry (traces, logs,
metrics) plus live SDK documentation.

## No build step

The dashboard is a **single self-contained HTML file** — `static/index.html`
(inline CSS + vanilla JS). There is **no npm/Node, no Vite, no bundler, and no
CDN dependency**. It ships as plain text in the Python package and renders by
fetching the dashboard's own JSON API with relative paths (`fetch("api/...")`),
so it works under any mount prefix (e.g. `/rouge`) without server-side
templating.

> This was a deliberate choice: a JS build step works on some machines and
> fails on others (Node versions, lockfiles, native deps). A bundled HTML file
> always works. The data-driven model mirrors how FastAPI serves Swagger UI
> (a small HTML shell that fetches a JSON document).

To change the UI, edit `static/index.html` directly. That's the whole workflow.

## Architecture

- **UI:** `static/index.html` — tabs for Overview / Traces / Logs / SDK Docs,
  polling `api/telemetry` every 5s and reading `api/sdk/schema`.
- **Backend:** `server.py` exposes the dashboard as a FastAPI `APIRouter`
  (`create_dashboard_router`) — telemetry ingestion (`/v1/traces`, `/v1/logs`,
  `/v1/metrics`, `/api/ingest`), retrieval (`/api/telemetry`), the SDK-docs API
  (`api.py`), and static serving of `static/`.

The router is attached to a user's app the FastAPI-idiomatic way (as routes via
`include_router(..., include_in_schema=False)`), not as a mounted sub-app — see
`rouge_ai.integrations.fastapi.mount_dashboard`.

## Usage

### Mounted on your FastAPI app (recommended)

```python
import rouge_ai
from fastapi import FastAPI

app = FastAPI()
rouge_ai.init(service_name="my-app")
rouge_ai.connect_fastapi(app)  # auto-attaches the dashboard at /rouge
```

Dashboard is served at `http://localhost:8000/rouge` (same port as your app).
Disable with `rouge_ai.init(..., auto_mount_dashboard=False)` or change the path
with `dashboard_auto_path="/my-path"`.

### Standalone server

```python
import rouge_ai

rouge_ai.init(service_name="my-app")
rouge_ai.launch_dashboard(port=10108)  # http://localhost:10108
```

## Files

```
dashboard/
├── server.py          # FastAPI router + standalone app
├── api.py             # SDK-documentation API routes
├── static/
│   └── index.html     # the entire UI (no build artifacts)
└── README.md
```
