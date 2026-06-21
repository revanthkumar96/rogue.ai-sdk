"""Rouge.AI demo — a minimal FastAPI app that showcases the SDK end to end.

Run it:

    pip install -e ".[fastapi]"
    python demo_app/main.py
    # open http://127.0.0.1:8000/rouge   (dashboard, auto-mounted like /docs)
    # open http://127.0.0.1:8000/docs     (FastAPI Swagger UI)

What it demonstrates:
  * rouge_ai.init() in pure local mode — no cloud, no AWS credentials, no
    external OTel collector. Spans are exported straight to the bundled
    dashboard's OTLP endpoint.
  * connect_fastapi(app) — auto-instruments every route AND auto-mounts the
    dashboard at /rouge.
  * @rouge_ai.trace — a traced sync helper and a traced async generator
    (streaming), so both span kinds show up in the dashboard.
  * rouge_ai.get_logger() — logs correlated to the active span.
"""

import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

import rouge_ai

HOST = "127.0.0.1"
PORT = 8000

# 1. Initialise Rouge in local-first mode: export spans to the dashboard that
#    connect_fastapi() mounts below. No cloud export, no AWS credentials, no
#    separate collector — everything runs in this one process.
rouge_ai.init(
    service_name="rouge-demo-app",
    local_mode=True,
    enable_span_cloud_export=True,  # use the OTLP exporter...
    enable_log_cloud_export=False,
    enable_log_console_export=True,
    otlp_endpoint=f"http://{HOST}:{PORT}/rouge/v1/traces",  # ...aimed here
    allow_insecure_transport=True,  # localhost http
)

logger = rouge_ai.get_logger("demo")

app = FastAPI(title="Rouge.AI Demo")


@rouge_ai.trace(
    rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
def summarize(text: str) -> str:
    """A traced helper standing in for a real LLM call."""
    logger.info("summarizing %d chars", len(text))
    words = text.split()
    return " ".join(words[:20]) + ("..." if len(words) > 20 else "")


@rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
async def stream_tokens(prompt: str):
    """A traced async generator standing in for a streaming LLM response."""
    for token in f"echo: {prompt}".split():
        await asyncio.sleep(0.05)
        yield token + " "


@app.get("/")
def index():
    return {
        "message":
        "Rouge.AI demo is running.",
        "dashboard":
        f"http://{HOST}:{PORT}/rouge",
        "docs":
        f"http://{HOST}:{PORT}/docs",
        "try": [
            f"http://{HOST}:{PORT}/summarize?text=hello+world",
            f"http://{HOST}:{PORT}/chat?prompt=hi"
        ],
    }


@app.get("/summarize")
def summarize_endpoint(text: str):
    return {"summary": summarize(text)}


@app.get("/chat")
async def chat_endpoint(prompt: str):

    async def body():
        async for token in stream_tokens(prompt):
            yield token

    return StreamingResponse(body(), media_type="text/plain")


# 2. Auto-instrument the app and auto-mount the dashboard at /rouge.
rouge_ai.connect_fastapi(app)

if __name__ == "__main__":
    print(f"Rouge.AI v{rouge_ai.__version__} demo")
    print(f"  dashboard: http://{HOST}:{PORT}/rouge")
    print(f"  swagger:   http://{HOST}:{PORT}/docs")
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    finally:
        rouge_ai.shutdown()
