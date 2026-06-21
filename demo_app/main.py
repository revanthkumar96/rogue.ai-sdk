"""Rouge.AI demo — a production-like local app exercising the full SDK.

One FastAPI service, fully observable through Rouge.AI, with a real Gemini
multi-agent. No cloud account, no AWS credentials, no external OpenTelemetry
collector: spans/logs export straight to the bundled dashboard.

Run:
    pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
    # .env must contain: GEMINI_API_KEY=...   (optional: GEMINI_MODEL=...)
    python demo_app/main.py
    # dashboard: http://127.0.0.1:8000/rouge   ·   swagger: .../docs

What it exercises (see DEMO_SPEC.md):
  * @trace sync / async / async-generator (streaming) + manual spans
  * trace_params / trace_return_value + write_attributes_to_current_span
  * get_logger() at every level, correlated to spans (shown as span events)
  * secret redaction (SensitiveDataFilter) on a logged-secret endpoint
  * error path -> ERROR span with recorded exception
  * head sampling (ROUGE_TRACES_SAMPLER_RATIO)
  * connect_fastapi route auto-instrumentation + dashboard auto-mount
  * instrument_llm -> real Gemini calls via a LangGraph multi-agent
  * a startup load burst so the dashboard graphs populate immediately
"""

import os
import threading
import time
import urllib.request

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

import rouge_ai
from rouge_ai.tracer import write_attributes_to_current_span

HOST = "127.0.0.1"
PORT = 8000
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Bridge: the user's key is GEMINI_API_KEY, but langchain-google-genai reads
# GOOGLE_API_KEY. Forward it so real Gemini calls authenticate.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# 1. Initialise Rouge in local-first mode: export to the dashboard mounted
#    below. Sampling ratio is configurable (default 1.0 so the demo shows all).
rouge_ai.init(
    service_name="rouge-demo",
    local_mode=True,
    enable_span_cloud_export=True,  # use the OTLP exporter...
    enable_log_cloud_export=False,
    enable_log_console_export=True,
    otlp_endpoint=f"http://{HOST}:{PORT}/rouge/v1/traces",  # ...aimed here
    allow_insecure_transport=True,
    traces_sampler_ratio=float(os.getenv("ROUGE_TRACES_SAMPLER_RATIO", "1.0")),
    llm_providers=["langchain", "googlegenai"],
)

logger = rouge_ai.get_logger("demo")
app = FastAPI(title="Rouge.AI Demo")

# --- Real Gemini multi-agent (LangGraph), built lazily ---------------------
_graph = None


def _build_graph():
    from typing import TypedDict

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import END, START, StateGraph

    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)

    class S(TypedDict):
        topic: str
        plan: str
        research: str
        draft: str

    def ask(prompt: str) -> str:
        r = llm.invoke(prompt)  # real Gemini call (auto-instrumented)
        return getattr(r, "content", str(r))

    @rouge_ai.trace(
        rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
    def planner(s):
        logger.info("planner: outlining %s", s["topic"])
        return {
            "plan":
            ask(f"Create a 3-bullet outline for an article about: "
                f"{s['topic']}. Bullets only.")
        }

    @rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
    def researcher(s):
        logger.info("researcher: gathering facts")
        # Manual span demonstrates a nested "tool" call inside an agent.
        with rouge_ai.get_tracer().start_as_current_span(
                "tool.kb_lookup") as sp:
            sp.set_attribute("tool.name", "kb_search")
            sp.set_attribute("tool.query", s["topic"])
        return {
            "research": ask(f"List 2 concrete facts per bullet:\n{s['plan']}")
        }

    @rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
    def writer(s):
        logger.info("writer: drafting article")
        return {
            "draft":
            ask(f"Write a concise 150-word article on "
                f"'{s['topic']}' using this outline:\n{s['plan']}\n"
                f"and these facts:\n{s['research']}")
        }

    g = StateGraph(S)
    g.add_node("planner", planner)
    g.add_node("researcher", researcher)
    g.add_node("writer", writer)
    g.add_edge(START, "planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "writer")
    g.add_edge("writer", END)
    return g.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


# --- Traced helpers --------------------------------------------------------
@rouge_ai.trace(
    rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
def summarize(text: str) -> str:
    """Traced sync helper (stand-in for a cheap local transform)."""
    logger.info("summarizing %d chars", len(text))
    words = text.split()
    return " ".join(words[:20]) + ("..." if len(words) > 20 else "")


@rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
async def stream_tokens(prompt: str):
    """Traced async generator (stand-in for a streaming response)."""
    import asyncio
    for token in f"echo: {prompt}".split():
        await asyncio.sleep(0.05)
        yield token + " "


@rouge_ai.trace()
def _risky_op():
    raise ValueError("intentional demo failure (G-ERR)")


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def run_pipeline(topic: str) -> dict:
    """Run the planner -> researcher -> writer Gemini multi-agent."""
    write_attributes_to_current_span({
        "agent.pipeline": "content",
        "user.tier": "demo"
    })
    final = get_graph().invoke({"topic": topic})
    return {"topic": topic, "plan": final["plan"], "draft": final["draft"]}


# --- Endpoints -------------------------------------------------------------
@app.get("/")
def index():
    return {
        "message": "Rouge.AI demo is running.",
        "dashboard": f"http://{HOST}:{PORT}/rouge",
        "docs": f"http://{HOST}:{PORT}/docs",
        "try": {
            "summarize": f"http://{HOST}:{PORT}/summarize?text=hello+world",
            "chat (stream)": f"http://{HOST}:{PORT}/chat?prompt=hi",
            "multi-agent (Gemini)":
            f"http://{HOST}:{PORT}/agent/run?topic=otel",
            "error span": f"http://{HOST}:{PORT}/boom",
            "secret redaction": f"http://{HOST}:{PORT}/login",
        },
        "model": MODEL,
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


@app.get("/agent/run")
def agent_run_get(topic: str = "OpenTelemetry tracing"):
    return run_pipeline(topic)


@app.post("/agent/run")
def agent_run(payload: dict):
    return run_pipeline(payload.get("topic", "OpenTelemetry tracing"))


@app.get("/boom")
def boom():
    """Deliberately fails -> ERROR span with recorded exception (G-ERR)."""
    _risky_op()


@app.get("/login")
def login(user: str = "ada"):
    """Logs secrets; the SensitiveDataFilter redacts them in telemetry (G-PII).

    The SDK's log filter redacts secrets it recognises — API keys, bearer
    tokens, passwords, and OpenAI/Anthropic ``sk-`` keys. (Email/card/phone
    redaction is handled separately, on HTTP request bodies, by the FastAPI
    body sanitizer.)
    """
    logger.info("auth user=%s api_key=%s password=%s bearer=%s", user,
                "sk-" + "a" * 48, "SuperSecretPassw0rd!", "Bearer " + "b" * 32)
    return {
        "status": "logged — secrets are redacted in the captured telemetry"
    }


# 2. Auto-instrument the app + auto-mount the dashboard at /rouge.
rouge_ai.connect_fastapi(app)


def _load_burst():
    """Fire a few requests after startup so the dashboard graphs populate."""
    time.sleep(2.0)
    paths = []
    for i in range(8):
        paths.append(f"/summarize?text=demo+load+request+number+{i}+words")
        paths.append(f"/login?user=user{i}")
    paths += ["/boom", "/boom"]  # a couple of error traces
    for p in paths:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}{p}",
                                   timeout=5).read()
        except Exception:
            pass  # /boom returns 500 by design


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GEMINI_API_KEY/GOOGLE_API_KEY not set — /agent/run "
              "(Gemini) will fail; other endpoints work. Add it to .env.")
    print(f"Rouge.AI v{rouge_ai.__version__} demo (model={MODEL})")
    print(f"  dashboard: http://{HOST}:{PORT}/rouge")
    print(f"  swagger:   http://{HOST}:{PORT}/docs")
    threading.Thread(target=_load_burst, daemon=True).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    finally:
        rouge_ai.shutdown()
