"""Gateway service (service.name = rouge-gateway) — edge API + dashboard host.

Part of the distributed demo. Hosts the dashboard at /rouge and calls the agent
service over HTTP with W3C tracecontext injected, so /agent/run and /agent/ping
produce a single trace spanning rouge-gateway -> rouge-agent.

Also serves the local endpoints (summarize / chat / boom / login) so the whole
SDK surface is exercised from one place. Run standalone for debugging:
    python demo_app/gateway.py   (needs the agent on :8100 for /agent/*)
"""

import asyncio
import os
import threading
import time
import urllib.request

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from opentelemetry.propagate import inject

import rouge_ai
from rouge_ai.tracer import write_attributes_to_current_span

HOST = "127.0.0.1"
PORT = 8000
AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:8100")

rouge_ai.init(
    service_name="rouge-gateway",
    local_mode=True,
    enable_span_cloud_export=True,
    enable_log_cloud_export=False,
    enable_log_console_export=True,
    otlp_endpoint=f"http://{HOST}:{PORT}/rouge/v1/traces",
    allow_insecure_transport=True,
    traces_sampler_ratio=float(os.getenv("ROUGE_TRACES_SAMPLER_RATIO", "1.0")),
)

logger = rouge_ai.get_logger("gateway")
app = FastAPI(title="Rouge Gateway")


# --- local traced work -----------------------------------------------------
@rouge_ai.trace(
    rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
def summarize(text: str) -> str:
    logger.info("summarizing %d chars", len(text))
    words = text.split()
    return " ".join(words[:20]) + ("..." if len(words) > 20 else "")


@rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
async def stream_tokens(prompt: str):
    for token in f"echo: {prompt}".split():
        await asyncio.sleep(0.05)
        yield token + " "


@rouge_ai.trace()
def _risky_op():
    raise ValueError("intentional demo failure (G-ERR)")


# --- cross-service calls (distributed tracing) -----------------------------
def _call_agent(path: str, **kwargs) -> dict:
    """Call the agent service, injecting trace context (G-MULTI)."""
    headers = {}
    inject(headers)  # adds W3C traceparent/baggage from the active span
    write_attributes_to_current_span({
        "downstream.service": "rouge-agent",
        "downstream.path": path
    })
    if kwargs:
        r = httpx.post(f"{AGENT_URL}{path}",
                       json=kwargs,
                       headers=headers,
                       timeout=60)
    else:
        r = httpx.get(f"{AGENT_URL}{path}", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def call_agent_run(topic: str) -> dict:
    return _call_agent("/run", topic=topic)


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def call_agent_ping(note: str) -> dict:
    return _call_agent(f"/ping?note={note}")


# --- endpoints -------------------------------------------------------------
@app.get("/")
def index():
    return {
        "message": "Rouge.AI distributed demo (gateway).",
        "dashboard": f"http://{HOST}:{PORT}/rouge",
        "services": ["rouge-gateway (:8000)", "rouge-agent (:8100)"],
        "try": {
            "summarize": f"http://{HOST}:{PORT}/summarize?text=hello+world",
            "chat (stream)": f"http://{HOST}:{PORT}/chat?prompt=hi",
            "distributed ping (no key)": f"http://{HOST}:{PORT}/agent/ping",
            "distributed multi-agent (Gemini)":
            f"http://{HOST}:{PORT}/agent/run?topic=otel",
            "error span": f"http://{HOST}:{PORT}/boom",
            "secret redaction": f"http://{HOST}:{PORT}/login",
        },
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


@app.get("/agent/ping")
def agent_ping(note: str = "hello"):
    """Distributed trace WITHOUT Gemini: gateway -> agent over HTTP."""
    return call_agent_ping(note)


@app.get("/agent/run")
def agent_run_get(topic: str = "OpenTelemetry tracing"):
    return call_agent_run(topic)


@app.post("/agent/run")
def agent_run(payload: dict):
    return call_agent_run(payload.get("topic", "OpenTelemetry tracing"))


@app.get("/boom")
def boom():
    _risky_op()


@app.get("/login")
def login(user: str = "ada"):
    """Logged secrets are redacted in telemetry by SensitiveDataFilter."""
    logger.info("auth user=%s api_key=%s password=%s bearer=%s", user,
                "sk-" + "a" * 48, "SuperSecretPassw0rd!", "Bearer " + "b" * 32)
    return {
        "status": "logged — secrets are redacted in the captured telemetry"
    }


# Auto-instrument the server + auto-mount the dashboard at /rouge.
rouge_ai.connect_fastapi(app)


def _load_burst():
    """Populate the dashboard graphs (incl. distributed traces) on startup."""
    time.sleep(2.5)
    paths = []
    for i in range(6):
        paths.append(f"/summarize?text=demo+load+request+number+{i}")
        paths.append(f"/agent/ping?note=burst{i}")  # distributed, no key
        paths.append(f"/login?user=user{i}")
    paths += ["/boom", "/boom"]
    for p in paths:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}{p}",
                                   timeout=10).read()
        except Exception:
            pass


if __name__ == "__main__":
    print(f"rouge-gateway on http://{HOST}:{PORT}  (dashboard: /rouge)")
    threading.Thread(target=_load_burst, daemon=True).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    finally:
        rouge_ai.shutdown()
