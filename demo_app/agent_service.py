"""Agent service (service.name = rouge-agent).

Part of the distributed demo. Hosts the real Gemini LangGraph multi-agent and a
key-free /ping. The gateway calls this over HTTP with W3C tracecontext
injected, so the agent's spans join the gateway's trace (one trace, two
services).

It exports spans to the dashboard the GATEWAY hosts (no dashboard of its own).
Run standalone for debugging:  python demo_app/agent_service.py
"""

import os

import uvicorn
from fastapi import FastAPI

import rouge_ai
from rouge_ai.tracer import write_attributes_to_current_span

HOST = "127.0.0.1"
PORT = 8100
# The gateway process hosts the dashboard at :8000/rouge; export there.
DASHBOARD_OTLP = os.getenv("ROUGE_DASHBOARD_OTLP",
                           "http://127.0.0.1:8000/rouge/v1/traces")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# GEMINI_API_KEY -> GOOGLE_API_KEY bridge (langchain-google-genai reads that).
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

rouge_ai.init(
    service_name="rouge-agent",
    local_mode=True,
    enable_span_cloud_export=True,
    enable_log_cloud_export=False,
    enable_log_console_export=True,
    otlp_endpoint=DASHBOARD_OTLP,
    allow_insecure_transport=True,
    auto_mount_dashboard=False,  # only the gateway hosts the dashboard
    llm_providers=["langchain", "googlegenai"],
)

logger = rouge_ai.get_logger("agent")
app = FastAPI(title="Rouge Agent Service")

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


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def run_pipeline(topic: str) -> dict:
    write_attributes_to_current_span({"agent.pipeline": "content"})
    final = get_graph().invoke({"topic": topic})
    return {"topic": topic, "plan": final["plan"], "draft": final["draft"]}


@app.get("/health")
def health():
    return {"status": "ok", "service": "rouge-agent"}


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def _do_ping(note: str) -> dict:
    logger.info("agent ping: %s", note)
    return {"pong": note, "service": "rouge-agent"}


@app.get("/ping")
def ping(note: str = "hello"):
    """Key-free endpoint so distributed tracing is demoable without Gemini."""
    return _do_ping(note)


@app.post("/run")
def run(payload: dict):
    return run_pipeline(payload.get("topic", "OpenTelemetry tracing"))


# Instrument the server: extracts the incoming traceparent so spans here join
# the caller's trace. No dashboard (auto_mount_dashboard=False above).
rouge_ai.connect_fastapi(app)

if __name__ == "__main__":
    print(f"rouge-agent on http://{HOST}:{PORT} (model={MODEL})")
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    finally:
        rouge_ai.shutdown()
