# Rouge.AI Demo Application

A production-like, **distributed**, local demo that exercises the **full**
Rouge.AI SDK — including **real Gemini** calls and **cross-process distributed
tracing** — all visible on the bundled dashboard. No cloud account, no AWS
credentials, no external OpenTelemetry collector. See `../DEMO_SPEC.md`.

## Two services, one trace

| Service         | Port | Role                                       |
| --------------- | ---- | ------------------------------------------ |
| `rouge-gateway` | 8000 | edge API + hosts the dashboard at `/rouge` |
| `rouge-agent`   | 8100 | real Gemini LangGraph multi-agent          |

The gateway calls the agent over HTTP with **W3C tracecontext injected**, so a
single trace spans `rouge-gateway → rouge-agent` (verified: traces span both
service names).

## Run

```bash
pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
# .env: GEMINI_API_KEY=...   (optional GEMINI_MODEL=gemini-2.0-flash)
python demo_app/main.py        # launches BOTH services
```

`main.py` starts `rouge-agent` (subprocess), waits for it, then starts
`rouge-gateway`. A startup load burst populates the dashboard immediately. Open:

- **Dashboard** — http://127.0.0.1:8000/rouge
- **Swagger** — http://127.0.0.1:8000/docs

## Endpoints (what each demonstrates)

| Endpoint                   | Demonstrates                                                                                                                |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `GET /summarize?text=...`  | `@trace` sync + `trace_params`/`trace_return_value`                                                                         |
| `GET /chat?prompt=...`     | `@trace` async generator (streaming span)                                                                                   |
| `GET /agent/ping?note=...` | **distributed trace, no key** — gateway → agent over HTTP                                                                   |
| `GET /agent/run?topic=...` | **distributed + real Gemini** multi-agent (planner→researcher→writer), nested agent/LLM spans, manual `tool.kb_lookup` span |
| `GET /boom`                | error path → **ERROR span** with recorded exception                                                                         |
| `GET /login?user=...`      | **secret redaction** — API keys/tokens/passwords redacted in telemetry                                                      |

## What to look for on the dashboard

1. **Traces** → open a `/agent/*` trace → **waterfall** showing spans from
   **both** `rouge-gateway` and `rouge-agent` (distributed); click a span for
   attributes, status, and events (the correlated `log.*` lines).
1. **Logs** → not empty (logs are span events in local mode); filter by level.
1. **Overview** → throughput, latency p50/p95/p99, success/error donut, LLM
   token usage, **spans by service** (two services).

## Notes

- **Key bridge:** both services read `GEMINI_API_KEY` and forward it as
  `GOOGLE_API_KEY` (which `langchain-google-genai` expects). Without a key, every
  endpoint except `/agent/run` still works — `/agent/ping` shows distributed
  tracing without Gemini.
- **Sampling:** set `ROUGE_TRACES_SAMPLER_RATIO` (default `1.0`).
- **Debugging:** each service is runnable standalone
  (`python demo_app/agent_service.py`, `python demo_app/gateway.py`).
- **Local-first:** `local_mode=True`; both services export to the gateway's
  dashboard. CloudWatch logging and cloud credential fetch are cloud-only and
  out of scope.
