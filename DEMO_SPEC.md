# Rouge.AI Demo & Dashboard Specification

> **Status:** specification (target state) — drives the demo + dashboard rework.
> **Goal:** a single, runnable, **production-like local** harness that exercises
> the **full** rouge-ai SDK end to end and renders **complete, informative**
> observability (full traces with a waterfall, graphs/metrics, and logs) on the
> bundled dashboard — no cloud account, no external collector.
> **Created:** 2026-06-21. Companion to `ROUGE_AI_TECHNICAL.md`.

______________________________________________________________________

## 0. Why this exists

The current demo (`demo_app/main.py`) starts, traces, and mounts the dashboard,
but it under-tests the SDK and the dashboard is thin:

- **Logs never appear** in the dashboard. In `local_mode` the logger emits logs
  as **span events** (and to the console), not as OTLP logs to `/v1/logs`, so
  the dashboard's Logs tab (which only shows `/v1/logs` ingests) is always
  empty.
- **Traces aren't fully visualized.** The UI is flat tables — no span
  hierarchy/waterfall, no timings, no attributes/events drill-down, no graphs.
- **The demo is trivial & single-service.** One process, `asyncio.sleep`-style
  work; it never exercises distributed context propagation, sampling, errors,
  concurrency/throughput, LLM token usage, PII redaction, or the manual span
  API — i.e. most of the SDK.

This document defines what "good" looks like so the demo and dashboard actually
prove rouge-ai works in conditions resembling production.

______________________________________________________________________

## 1. Definition of done (acceptance criteria)

A reviewer running **one command** (`python demo_app/main.py`, with
`GEMINI_API_KEY` in `.env`) and opening `http://127.0.0.1:8000/rouge` must be
able to, **without any extra setup**:

1. See a **live trace list** that updates as requests arrive.
1. Open any trace and see a **waterfall / flamegraph**: every span with its
   parent→child nesting, start offset, and duration bar.
1. Open a span and see its **attributes, status (OK/ERROR), recorded
   exceptions, and events** (including the correlated `log.*` events).
1. See a **Logs view** that is **not empty** — log lines at every level
   (debug→critical), each linked to its trace/span, filterable by level.
1. See **graphs/metrics**: request throughput over time, latency
   distribution (p50/p95/p99), error rate, span count, and **LLM token usage**.
1. See **multiple services** in the trace (a gateway service calling an agent
   service) proving **context propagation** across process boundaries.
1. See **LLM spans** from real **Gemini** calls (via the LangGraph multi-agent),
   with model, prompt/response (when content capture is on), and token counts.
1. Confirm **PII is redacted** — a request carrying a fake email/card/phone
   shows redacted values in the captured attributes/logs.
1. See at least one **deliberately failing** request rendered as an **ERROR**
   span with the exception recorded.
1. Read the **SDK Docs** tab (introspected decorators/functions/config).

If any of the 10 cannot be done from a cold `git clone` + `pip install` + one
run, the demo is incomplete.

______________________________________________________________________

## 2. Full SDK surface the demo MUST exercise

Every row maps to a concrete, visible behavior in the demo. (Refs:
`ROUGE_AI_TECHNICAL.md`.)

| SDK capability                                                       | How the demo exercises it                             | Visible where                           |
| -------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------- |
| `init()` config precedence (env > kwargs > YAML)                     | ship a `.rouge-config.yaml` + `ROUGE_*` env overrides | startup log / SDK Docs                  |
| `@trace` **sync**                                                    | a plain handler                                       | trace waterfall                         |
| `@trace` **async**                                                   | an async handler                                      | trace waterfall                         |
| `@trace` **generator** + **async-generator**                         | a streaming endpoint (token stream)                   | one span spanning the full stream       |
| `trace_params` / `trace_return_value`                                | enabled on agent nodes                                | span attributes `params.*`, `return`    |
| Manual spans (`get_tracer().start_as_current_span`)                  | an inner "tool" span inside an agent                  | nested span in waterfall                |
| `write_attributes_to_current_span`                                   | attach business attrs (e.g. `user.tier`)              | span attributes                         |
| `get_logger()` at all levels                                         | debug/info/warning/error/critical around the work     | Logs view + span events                 |
| Log↔trace correlation                                                | every log carries trace_id/span_id                    | Logs view links to trace                |
| **Per-span log counters** (`num_*_logs`)                             | naturally produced by logging                         | span attributes                         |
| **PII redaction** (`sanitize_telemetry_data`, `SensitiveDataFilter`) | send fake email/SSN/card/phone                        | redacted in attrs/logs                  |
| `connect_fastapi` route auto-instrumentation                         | all HTTP routes                                       | server spans w/ http.method/path/status |
| Header/body sanitization                                             | send Authorization + a JSON body                      | redacted headers; body preview gated    |
| `instrument_llm` (Gemini + LangChain)                                | LangGraph multi-agent calling Gemini                  | LLM spans w/ token usage                |
| **Sampling** (`traces_sampler_ratio` / `OTEL_TRACES_SAMPLER`)        | set ratio < 1.0 on a high-volume endpoint             | fewer traces than requests (documented) |
| **Exporter by scheme** (http/grpc)                                   | export to the dashboard via OTLP/HTTP                 | traces land in dashboard                |
| Propagators / **distributed tracing**                                | gateway → agent service over HTTP                     | one trace spanning 2 services           |
| Resource attributes                                                  | service.name/version/environment per service          | span resource / service map             |
| Error path → span **status ERROR** + `record_exception`              | an endpoint that raises                               | ERROR span in waterfall                 |
| Concurrency / throughput                                             | a small built-in load generator                       | throughput/latency graphs               |
| `shutdown()` flush                                                   | on process exit                                       | clean shutdown, no lost spans           |
| Dashboard security (localhost gate / auth / CORS)                    | default localhost-only; documented opt-ins            | 403 from non-local (documented)         |
| Introspection/registry/schema                                        | auto-populated                                        | SDK Docs tab                            |

> Anything in `ROUGE_AI_TECHNICAL.md` not listed here is explicitly **out of
> demo scope** (e.g. AWS CloudWatch logging, cloud credential fetch) because the
> demo is local-first; call those out in the demo README as "cloud-only".

______________________________________________________________________

## 3. "Production environment, locally" — what that means here

The demo must resemble a real deployment, not a toy:

- **Multiple services in one process group.** At minimum a **gateway** service
  and an **agent** service, each with its own `service_name`/resource, wired so
  a request to the gateway calls the agent over HTTP and the **trace propagates**
  (W3C tracecontext) into a single end-to-end trace. This proves the headline
  distributed-tracing value.
- **Realistic config surface.** Config comes from `.rouge-config.yaml` +
  `ROUGE_*`/`OTEL_*` env (not all hardcoded), including a **sampler ratio**, an
  explicit **OTLP endpoint**, content-capture flags, and `instrument_llm`
  allow-list (`langchain`, `googlegenai`).
- **Real LLM workload.** A **LangGraph multi-agent** (planner → researcher →
  writer) backed by **Gemini** (`GEMINI_API_KEY` from `.env`), so traces include
  real, variable-latency LLM spans with token usage and nested agent spans.
- **Failure & edge cases.** At least one endpoint that raises (ERROR span), one
  that streams (generator span), one that carries PII (redaction), and one
  high-volume endpoint under the built-in load generator (sampling + graphs).
- **No external infra.** No Docker, no OTel Collector, no cloud keys beyond the
  Gemini key. Spans/logs/metrics go straight to the bundled dashboard.

### Suggested demo shape

```
demo_app/
  main.py            # entrypoint: starts gateway + agent, optional load-gen
  gateway.py         # FastAPI "edge" service: routes, PII endpoint, error endpoint,
                     #   streaming endpoint, calls agent service over HTTP
  agent_service.py   # FastAPI service hosting the LangGraph + Gemini multi-agent
  loadgen.py         # fires N concurrent requests to populate graphs
  .rouge-config.yaml # demo config (service names, sampling, endpoint, llm allow-list)
  README.md          # one-command run + what to look for (maps to §1)
```

(Single-process is acceptable if two FastAPI apps run on two ports via one
launcher; the point is two **services** with propagated context.)

______________________________________________________________________

## 4. Dashboard requirements (the informative part)

The dashboard must move from flat tables to a real trace explorer. Required
views/components:

### 4.1 Trace explorer

- **Trace list:** time, root span name, service, duration, status, span count;
  newest-first; live-updating; clickable.
- **Waterfall / flamegraph (REQUIRED):** for a selected trace, render the span
  tree with horizontal time bars (start offset + duration), nesting/indent by
  parent→child, color by service and by status (error = red). This is the
  single most important missing piece.
- **Span detail panel:** name, service, kind, start/end, duration, status +
  status message, **all attributes** (incl. `params.*`, `return`, `http.*`,
  `gen_ai.*`/token usage, `num_*_logs`), and **events** (each `log.*` event with
  level/message/timestamp), and recorded exceptions/stacktrace.

### 4.2 Logs view (must not be empty)

- Source logs from **both** OTLP logs (`/v1/logs`) **and** span **events**
  (`log.*`) extracted from traces — in `local_mode` logs arrive as span events,
  so the frontend MUST surface those, otherwise the tab is always empty.
- Columns: timestamp, level (color-coded), logger, message, trace_id/span_id
  (link to the trace/span).
- Filters: by level (debug→critical), by service, free-text search.

### 4.3 Metrics & graphs

- **Throughput** (requests/spans per second) over a rolling window.
- **Latency distribution**: p50/p95/p99 (per endpoint and overall).
- **Error rate** over time.
- **LLM token usage** (prompt/completion/total) over time and per model.
- **Span volume** by service/operation.
- Graphs derived from the in-memory store client-side (no new backend deps), or
  via a small aggregation endpoint if needed.

### 4.4 Service map (nice-to-have, strongly desired)

- A simple node-link graph of services and call edges derived from spans
  (gateway → agent → Gemini), with error edges highlighted.

### 4.5 Cross-cutting

- **Live updates** (existing 5s poll is acceptable; WebSocket optional).
- **Search/filter** across traces (service, name, status, time range).
- Keep the **build-free** constraint: vanilla JS + inline CSS in
  `dashboard/static/index.html`; a small charting approach that needs **no npm
  build** (hand-drawn SVG/canvas, or a single vendored dependency-free helper).
  No React/Vite build pipeline.

______________________________________________________________________

## 5. Known gaps to close (current → target)

| #             | Gap (current)                      | Target                                           | Likely change                                                                                                                                |
| ------------- | ---------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| G-LOG         | Logs tab empty in local mode       | Logs view shows span-event logs                  | frontend: extract `log.*` events from traces; (optional) add an OTLP-logs-to-dashboard path                                                  |
| G-WF          | No waterfall/flamegraph            | Full span-tree waterfall                         | frontend: build tree from spans (traceId/spanId/parentSpanId) + time bars                                                                    |
| G-GRAPH       | No metrics graphs                  | Throughput/latency/error/token graphs            | frontend: aggregate store; SVG/canvas charts (no build)                                                                                      |
| G-DETAIL      | No span drill-down                 | Attributes + events + status panel               | frontend: span detail view                                                                                                                   |
| G-MULTI       | ✅ DONE — gateway + agent services | Gateway + agent services, propagated trace       | `gateway.py`+`agent_service.py`+`main.py`; gateway injects W3C tracecontext on the HTTP call → one trace spans both service names (verified) |
| G-LLM         | No real LLM spans                  | Gemini via LangGraph multi-agent                 | demo: wire `multiagent.py` into the flow w/ `GEMINI_API_KEY`                                                                                 |
| G-ERR         | No error/exception traces          | ERROR span demo                                  | demo: failing endpoint                                                                                                                       |
| G-PII         | Redaction not demonstrated         | PII endpoint shows redaction                     | demo: endpoint with fake PII                                                                                                                 |
| G-SAMP        | Sampling not shown                 | Sampler ratio on a load endpoint                 | demo + loadgen                                                                                                                               |
| G-METRICS-SDK | SDK emits no metrics               | (stretch) emit basic metrics, or document as N/A | note: rouge currently exports traces+logs; metrics graphs derive from spans                                                                  |

> Note on naming: the user's `.env` key is **`GEMINI_API_KEY`**. `langchain- google-genai` reads **`GOOGLE_API_KEY`**. The demo must bridge this: read
> `GEMINI_API_KEY` and set/forward it as `GOOGLE_API_KEY` (or pass
> `google_api_key=` explicitly to `ChatGoogleGenerativeAI`).

______________________________________________________________________

## 6. Run contract

```bash
pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
# .env must contain: GEMINI_API_KEY=...
python demo_app/main.py
# open http://127.0.0.1:8000/rouge   -> Traces / Logs / Metrics / SDK Docs
# the launcher fires a short load burst so graphs are populated immediately
```

Exit (`Ctrl+C`) must `shutdown()` cleanly and flush. No collector, no Docker,
no cloud credentials.

______________________________________________________________________

## 7. Out of scope (call out, don't implement)

- AWS CloudWatch logging and cloud credential fetch (cloud-only; the demo is
  local-first).
- Durable/persistent telemetry storage (dashboard store stays in-memory, 500-item
  cap) — fine for a demo; note it's not durable.
- Auth/multi-tenant dashboard hardening beyond the existing localhost gate.

______________________________________________________________________

## 8. Implementation order (when we build it)

1. **Dashboard waterfall + span detail** (G-WF, G-DETAIL) — biggest value.
1. **Logs view from span events** (G-LOG) — fixes the empty Logs tab.
1. **Metrics graphs** (G-GRAPH) — throughput/latency/error/token.
1. **Demo rework**: gateway + agent services with propagated trace (G-MULTI),
   Gemini multi-agent wired in (G-LLM), error/PII/streaming endpoints (G-ERR,
   G-PII), loadgen + sampling (G-SAMP).
1. **README** mapping each acceptance-criterion (§1) to a click path.

Each step ships test-first, pre-commit clean, on its own commit in the PR.
