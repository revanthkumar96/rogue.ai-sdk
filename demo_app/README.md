# Rouge.AI Demo Application

A single, production-like local FastAPI app that exercises the **full** Rouge.AI
SDK end to end — including a **real Gemini multi-agent** — and renders everything
on the bundled dashboard. No cloud account, no AWS credentials, no external
OpenTelemetry collector. See `../DEMO_SPEC.md` for the full specification.

## Run

```bash
pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
# .env must contain your Gemini key:
#   GEMINI_API_KEY=...           (bridged to GOOGLE_API_KEY automatically)
#   GEMINI_MODEL=gemini-2.0-flash   (optional)
python demo_app/main.py
```

Open:

- **Dashboard** — http://127.0.0.1:8000/rouge (Overview / Traces / Logs / SDK Docs)
- **Swagger** — http://127.0.0.1:8000/docs

A short **load burst** fires on startup so the dashboard graphs populate
immediately.

## Endpoints (what each one demonstrates)

| Endpoint                   | Demonstrates                                                                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /summarize?text=...`  | `@trace` **sync** + `trace_params`/`trace_return_value`                                                                                                             |
| `GET /chat?prompt=...`     | `@trace` **async generator** (streaming span covers the whole stream)                                                                                               |
| `GET /agent/run?topic=...` | **real Gemini** LangGraph multi-agent (planner→researcher→writer), nested agent + LLM spans, a manual `tool.kb_lookup` span, and `write_attributes_to_current_span` |
| `GET /boom`                | error path → **ERROR span** with recorded exception                                                                                                                 |
| `GET /login?user=...`      | **secret redaction** — logged API keys / tokens / passwords are redacted in telemetry by `SensitiveDataFilter`                                                      |

## What to look for on the dashboard

1. **Traces** → click a trace → **waterfall** with parent→child nesting; click a
   span → attributes, status, and events (the correlated `log.*` lines).
1. **Logs** → not empty (logs arrive as span events in local mode); filter by
   level; click through to the trace.
1. **Overview** → throughput, latency distribution (p50/p95/p99), success/error
   donut, LLM token usage, spans-by-service.
1. `/agent/run` produces the richest trace: the agent pipeline with three real
   Gemini calls and a nested tool span.

## Notes

- **Key bridge:** the app reads `GEMINI_API_KEY` and forwards it as
  `GOOGLE_API_KEY` (which `langchain-google-genai` expects). Without a key, every
  endpoint except `/agent/run` still works.
- **Sampling:** set `ROUGE_TRACES_SAMPLER_RATIO` (default `1.0`) to head-sample.
- **Local-first:** `local_mode=True`; spans export to the bundled dashboard. AWS
  CloudWatch logging and cloud credential fetch are **cloud-only** and out of
  scope for this demo.
- **Single service:** this demo is one service with deep nested traces. True
  cross-process distributed tracing (two service names, propagated context) is
  the remaining DEMO_SPEC item (G-MULTI).
