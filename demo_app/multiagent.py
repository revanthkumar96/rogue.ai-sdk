"""Live multi-agent demo: LangGraph + Gemini, traced end to end by Rouge.AI.

A small 3-agent content pipeline (planner -> researcher -> writer) built with
LangGraph, each agent backed by Google Gemini, exposed over FastAPI, and fully
observable through Rouge.AI: every graph node is a @trace span and the
underlying LLM calls are auto-instrumented, all visible on the auto-mounted
dashboard at /rouge.

This is a DEMO, not a production agent — no retries, guardrails, persistence,
or auth on the agent itself.

Setup:
    pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
    # put your key in .env (or the environment):
    #   GOOGLE_API_KEY=...        (langchain-google-genai reads this)
    #   GEMINI_MODEL=gemini-2.0-flash   (optional override)

Run:
    python demo_app/multiagent.py
    # then:
    #   open  http://127.0.0.1:8000/rouge          (Rouge dashboard)
    #   POST  http://127.0.0.1:8000/agent/run      {"topic": "..."}
    #   or    http://127.0.0.1:8000/agent/run?topic=otel+tracing (GET helper)

# pattern: langgraph@1.2.2 graph/__init__.py (StateGraph + START/END edges)
"""

import os
from typing import TypedDict

import uvicorn
from fastapi import FastAPI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

import rouge_ai

HOST = "127.0.0.1"
PORT = 8000
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# 1. Rouge in local-first mode: spans go to the dashboard mounted below.
rouge_ai.init(
    service_name="rouge-multiagent-demo",
    local_mode=True,
    enable_span_cloud_export=True,
    enable_log_cloud_export=False,
    enable_log_console_export=True,
    otlp_endpoint=f"http://{HOST}:{PORT}/rouge/v1/traces",
    allow_insecure_transport=True,
    # Auto-instrument LangChain (and Gemini) LLM calls under each span.
    llm_providers=["langchain", "googlegenai"],
)

logger = rouge_ai.get_logger("multiagent")

# One shared Gemini client; LLM calls are auto-instrumented by Rouge.
_llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0.3)


class AgentState(TypedDict):
    topic: str
    plan: str
    research: str
    draft: str


def _ask(role: str, prompt: str) -> str:
    """Single Gemini turn for an agent role."""
    resp = _llm.invoke(prompt)
    return resp.content if hasattr(resp, "content") else str(resp)


@rouge_ai.trace(
    rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
def planner(state: AgentState) -> dict:
    """Agent 1 — break the topic into an outline."""
    logger.info("planning topic: %s", state["topic"])
    plan = _ask(
        "planner", f"Create a 3-bullet outline for an article about: "
        f"{state['topic']}. Bullets only.")
    return {"plan": plan}


@rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
def researcher(state: AgentState) -> dict:
    """Agent 2 — expand the outline with key facts."""
    logger.info("researching plan")
    research = _ask(
        "researcher", f"For this outline, list 2 concrete facts per bullet:\n"
        f"{state['plan']}")
    return {"research": research}


@rouge_ai.trace(rouge_ai.TraceOptions(trace_return_value=True))
def writer(state: AgentState) -> dict:
    """Agent 3 — write a short article from plan + research."""
    logger.info("writing draft")
    draft = _ask(
        "writer", f"Write a concise 150-word article on '{state['topic']}' "
        f"using this outline:\n{state['plan']}\n\nand these facts:\n"
        f"{state['research']}")
    return {"draft": draft}


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner)
    g.add_node("researcher", researcher)
    g.add_node("writer", writer)
    g.add_edge(START, "planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "writer")
    g.add_edge("writer", END)
    return g.compile()


GRAPH = _build_graph()

app = FastAPI(title="Rouge.AI Multi-Agent Demo")


@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True))
def run_pipeline(topic: str) -> dict:
    """Run the full planner -> researcher -> writer graph for a topic."""
    final = GRAPH.invoke({"topic": topic})
    return {"topic": topic, "plan": final["plan"], "draft": final["draft"]}


@app.get("/")
def index():
    return {
        "message": "Rouge.AI multi-agent demo (LangGraph + Gemini).",
        "dashboard": f"http://{HOST}:{PORT}/rouge",
        "run": f"http://{HOST}:{PORT}/agent/run?topic=distributed+tracing",
        "model": MODEL,
    }


@app.get("/agent/run")
def agent_run_get(topic: str):
    return run_pipeline(topic)


@app.post("/agent/run")
def agent_run(payload: dict):
    return run_pipeline(payload.get("topic", "OpenTelemetry tracing"))


# 2. Auto-instrument the app + auto-mount the dashboard at /rouge.
rouge_ai.connect_fastapi(app)

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY is not set — Gemini calls will fail. "
              "Add it to .env or the environment.")
    print(f"Rouge.AI multi-agent demo (model={MODEL})")
    print(f"  dashboard: http://{HOST}:{PORT}/rouge")
    print(f"  run:       http://{HOST}:{PORT}/agent/run?topic=hello")
    try:
        uvicorn.run(app, host=HOST, port=PORT)
    finally:
        rouge_ai.shutdown()
