# Rouge.AI SDK — Low-Level Technical Reference

> Source-derived reference for `rouge-ai` (this repo). All `file:line` refs point at `src/rouge_ai/`.
> Generated 2026-06-21 from working tree on branch `fix/safe-defaults-cleanup-and-demo`.

______________________________________________________________________

## 1. Identity & packaging

| Field                     | Value                                                     | Source                               |
| ------------------------- | --------------------------------------------------------- | ------------------------------------ |
| Distribution name         | `rouge-ai`                                                | `pyproject.toml:6`                   |
| Import package            | `rouge_ai` (src-layout)                                   | `pyproject.toml:127-130`             |
| Version                   | `0.0.10`                                                  | `pyproject.toml:7`, `__init__.py:16` |
| Description               | "The SDK that revolutionizes debugging and tracing."      | `pyproject.toml:8`                   |
| Self-description (schema) | "Production-ready observability SDK for LLM applications" | `schema.py:27`                       |
| License                   | Apache-2.0                                                | `pyproject.toml:11`                  |
| Python                    | `requires-python >=3.10` (classifiers list 3.10–3.12)     | `pyproject.toml:10,21-23`            |
| Status                    | Development Status :: 3 - Alpha                           | `pyproject.toml:17`                  |
| Build backend             | setuptools (`>=45`) + wheel                               | `pyproject.toml:1-3`                 |
| Repo                      | github.com/revanthkumar96/rouge.ai-sdk                    | `pyproject.toml:120`                 |

**What it is:** an OpenTelemetry-based LLM-observability/tracing SDK. Decorator + auto-instrumentation tracing → OTLP export; trace-correlated logging → AWS CloudWatch (or span events); a bundled self-hosted dashboard that doubles as an OTLP receiver. **No** voice/TTS/telephony and **no** alerting/event-trigger surface.

### Dependencies (all pinned)

Runtime (`pyproject.toml:30-47`): `opentelemetry-{api,sdk,exporter-otlp,exporter-otlp-proto-common/-grpc/-http,proto,semantic-conventions}==1.34.1`; `opentelemetry-instrumentation{,-asgi,-fastapi}==0.55b1`; `opentelemetry-util-http==0.55b1`; `opentelemetry-sdk-extension-aws==2.1.0`; `opentelemetry-propagator-aws-xray==1.0.2`; `watchtower==3.4.0` (CloudWatch); `PyYAML==6.0.2`.

Extras (`pyproject.toml:49-116`):

- `fastapi` → `fastapi==0.115.12`, `uvicorn==0.34.3`, `httpx==0.27.0`, `opentelemetry-instrumentation-fastapi==0.55b1`
- `llm` → 12 OTel instrumentors: openai, anthropic, cohere, mistralai, llamaindex, haystack, bedrock, vertexai, replicate, google-generativeai, langchain (unpinned)
- `dev` → pytest 8.4.1, pytest-asyncio 1.1.0, black 25.1.0, pre-commit 4.2.0, flake8 7.3.0, mypy 1.17.0
- `all` → union of the above

______________________________________________________________________

## 2. Public API surface (`__init__.py`)

```python
rouge_ai.init(**kwargs) -> TracerProvider          # main entrypoint
rouge_ai.trace(options: TraceOptions = TraceOptions())  # decorator factory
rouge_ai.get_tracer(name: str | None = None) -> opentelemetry.trace.Tracer
rouge_ai.get_logger(name: str | None = None) -> RougeLogger
rouge_ai.shutdown() -> None                         # flush + stop tracing & logging
rouge_ai.launch_dashboard(port=10108, host="0.0.0.0")
rouge_ai.connect_fastapi(app)                       # auto-instrument a FastAPI app
rouge_ai.mount_dashboard(app, path=None)            # attach dashboard routes
rouge_ai.RougeConfig            # dataclass
rouge_ai.TraceOptions           # dataclass
rouge_ai.__version__
```

Submodules are lazy-imported inside each facade fn (`__init__.py:33-61`) so importing the package is cheap and tolerant of missing extras.

______________________________________________________________________

## 3. Initialization & config resolution (`tracer.py:170-339`)

`init()` precedence (highest wins): **env vars > kwargs > YAML file** (`tracer.py:205-210`).

- YAML discovered by `find_rouge_config()` (`utils/config.py`) — looks for `.rouge-config.yaml`.
- Env parsing in `_load_env_config()` (`tracer.py:91-135`); bools accept `true/1/yes/on`; list fields comma-split; `traces_sampler_ratio` → float; everything else passes `validate_config_value()` (`utils/security.py`).
- `init()` with **no** resolvable config raises `ValueError` (honours its `-> TracerProvider` contract) rather than returning `None`.

**Provider lifecycle (OTel = one provider per process):**

- If a `ProxyTracerProvider` is installed → create `TracerProvider(resource, sampler)` and set global (`tracer.py:284-295`).
- If a real provider already exists → **reuse** it (never override the global; overriding orphans already-instrumented libs).
- Re-`init()` with kwargs reuses the provider but refreshes config + logger (`tracer.py:194-246`).
- `shutdown_tracing()` force-flushes + shuts down, then `_reset_global_tracer_provider()` pokes OTel internals (`_TRACER_PROVIDER_SET_ONCE = Once()`, `_TRACER_PROVIDER = None`) under a `threading.Lock` so a later `init()` can install fresh (`tracer.py:342-377`).

**Resource attributes** (`tracer.py:251-269`): `service.name`, `service.github_owner`, `service.github_repo_name`, `service.version` (= commit hash), `service.environment`. Merged with OTel SDK defaults + `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME`.

**Span processors** (`tracer.py:297-318`): optional `SimpleSpanProcessor(ConsoleSpanExporter)` (when `enable_span_console_export`); `BatchSpanProcessor(<otlp exporter>)` (when `enable_span_cloud_export`).

**Exporter selection** `_create_span_exporter()` (`tracer.py:138-167`): chooses gRPC vs HTTP by `OTEL_EXPORTER_OTLP_PROTOCOL` (`grpc` | `http/protobuf`), else by endpoint scheme (`grpc`/`grpcs`→gRPC, `http`/`https`→HTTP). Default **HTTP/protobuf**. `grpcs`⇒TLS, `grpc`⇒insecure. Still honours `OTEL_EXPORTER_OTLP_HEADERS`/`_TIMEOUT`. (Pattern credited to openllmetry `traceloop-sdk@0.61.0`.)

**Propagators** (`tracer.py:326-333`): installs `CompositePropagator([TraceContextTextMapPropagator, W3CBaggagePropagator])` **only if** `OTEL_PROPAGATORS` is unset (won't clobber a user's custom setup).

**Sampler** (`tracer.py:278-282`): explicit `traces_sampler_ratio` → `ParentBased(TraceIdRatioBased(ratio))`; else `None` (SDK honours `OTEL_TRACES_SAMPLER`).

______________________________________________________________________

## 4. `RougeConfig` (`config.py:8-86`)

Dataclass; `service_name` is the only required field. Full field set & defaults:

| Category       | Fields (default)                                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identification | `service_name` (req) · `github_owner/repo_name/commit_hash` ("unknown") · `name=None` · `token=None`                                                               |
| AWS            | `aws_access_key_id/secret_access_key/session_token=None` · `aws_region="us-west-2"`                                                                                |
| OpenTelemetry  | `otlp_endpoint="https://localhost:4318/v1/traces"` · `traces_sampler_ratio=None`                                                                                   |
| Environment    | `environment="development"`                                                                                                                                        |
| Export toggles | `enable_span_console_export=False` · `enable_log_console_export=True` · `enable_span_cloud_export=True` · `enable_log_cloud_export=True` · `local_mode=False`      |
| Verification   | `verification_endpoint=` `https://api.prod1.rouge.ai/v1/verify/credentials` (`constants.py:3`)                                                                     |
| Verbose        | `tracer_verbose=False` · `logger_verbose=False`                                                                                                                    |
| LLM            | `instrument_llm=True` · `llm_providers=None` (allow-list) · `llm_block_providers=None` (block-list)                                                                |
| Security       | `allow_insecure_transport=False` · `log_response_bodies=False` · `log_request_bodies=False` · `sanitize_telemetry_data=True`                                       |
| Dashboard      | `dashboard_username/password=None` · `auto_mount_dashboard=True` · `dashboard_auto_path="/rouge"` · `dashboard_allow_remote=False` · `dashboard_cors_origins=None` |

**Endpoint security** `_validate_endpoint_security()` (`config.py:96-160`), runs in `__post_init__`:

- Blocks SSRF cloud-metadata hosts: `169.254.169.254`, `metadata.google.internal`, `metadata`.
- `http`/`grpc` allowed only for `localhost`/`127.0.0.1`/`::1`, **or** with `allow_insecure_transport=True` (then warns to stderr).
- Valid schemes: `http`, `https`, `grpc`, `grpcs`.

**Env var mapping** (`constants.py:7-36`): `ROUGE_<FIELD>` → field, e.g. `ROUGE_SERVICE_NAME`, `ROUGE_OTLP_ENDPOINT`, `ROUGE_TRACES_SAMPLER_RATIO`, `ROUGE_LOCAL_MODE`, `ROUGE_INSTRUMENT_LLM`, `ROUGE_LLM_PROVIDERS`, `ROUGE_LLM_BLOCK_PROVIDERS`, `ROUGE_DASHBOARD_ALLOW_REMOTE`, `ROUGE_DASHBOARD_CORS_ORIGINS`, AWS + github + verification + verbose toggles.

______________________________________________________________________

## 5. `@trace` decorator & `TraceOptions` (`tracer.py:69-88, 419-675`)

```python
@dataclass
class TraceOptions:
    span_name: str | None = None
    span_name_suffix: str | None = None
    trace_params: bool | Sequence[str] = False   # True = all params, or a name list
    trace_return_value: bool = False
    flatten_attributes: bool = True
```

- Default span name = `f"{fn.__module__}.{fn.__qualname__}"` (`get_span_name`, `:82-88`).
- **Four wrapper kinds**, dispatched by `inspect` (`:568-575`): sync, coroutine, generator, async-generator. Generator/async-gen wrappers iterate **inside** the span so the span covers the full stream (not ~0 ms) — pattern from openllmetry `base.py:278-279` (`:537-563`).
- No-op when tracing isn't initialized (`_trace`, `:419-431`); span-creation failures degrade to no-op (`:447-454`).
- Standard attributes set on every traced span (guarded by an `_config is not None` check against shutdown races): `hash` (= `_name`, only when not `local_mode`), `service_name`, `service_environment`, `telemetry_sdk_language="python"`.
- Params recorded as `params.<name>` (`self` excluded) (`_params_to_dict`, `:611-635`); return value as `return` (`:523-525`).
- Value handling (`_store_dict_in_span`/`_coerce_attr_value`, `:599-655`): only bool/int/float/str/bytes kept verbatim; everything else `json.dumps(default=str)`; strings truncated to `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` (or `OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT`) when set. Nested dicts flattened with `_` via `_flatten_dict` (pure-Python `json_normalize` replacement; pandas was dropped) (`:658-675`).
- Each `@trace` registers the fn in the introspection registry (`:508-517`).

Manual API: `write_attributes_to_current_span(attributes: dict)` (`:580-584`) writes onto the active span if recording.

______________________________________________________________________

## 6. Logging (`logger.py`)

`RougeLogger` (`:288-647`) — trace-correlated structured logger, level DEBUG, UTC time.

- **Handlers** chosen at construction (`:328-341`): console (`enable_log_console_export`); **CloudWatch** when not `local_mode` and `enable_span_cloud_export`; otherwise the **span-event** handler (local mode).
- `SensitiveDataFilter` (`:17-89`) regex-redacts: AWS access/secret/session keys, generic `token`/`api_key`/`bearer` (≥20 chars), OpenAI `sk-…`, Anthropic `sk-ant-…`, `password`. Applied to every record.
- `TraceIdFilter` (`:116-230`) injects `trace_id` (AWS X-Ray format `1-{8hex}-{24hex}`), `span_id`, `parent_span_id`, `span_name`, a cleaned `stack_trace` (repo-relative), and service metadata.
- `SpanEventHandler` (`:233-285`) attaches each log as a span event `log.<level>` with `log.level/logger/message/module/function/lineno` + correlation attrs, timestamped in ns.
- CloudWatch via `watchtower.CloudWatchLogHandler` (`:428-437`): `use_queues=False`, `send_interval=0.05`, `max_batch_size=1`, `create_log_group=True`; log group = credentials `hash` or `config._name`, stream = `f"{service_name}-{environment}"`.
- Credential refresh: `_check_and_refresh_credentials()` on every log call; `refresh_credentials(force_refresh=True)` recreates the CW handler (`:507-604`).
- Log methods (`debug/info/warning/error/critical`) increment per-span counters `num_<level>_logs` (`:606-647`).
- `get_logger()` raises `RuntimeError` if `init()` hasn't run (`:712-727`).

______________________________________________________________________

## 7. Integrations (`integrations/`)

No generic plugin framework — two hardcoded modules.

### `connect_fastapi(app)` (`integrations/fastapi.py:128-241`)

Wraps `FastAPIInstrumentor.instrument_app(...)` with three hooks:

- `server_request_hook` → adds `service.*`, `http.path`, `http.method`.
- `client_request_hook` → adds `http.status_code` + **sanitized** headers.
- `client_response_hook` → optional body preview (only if `log_response_bodies`; max 200 chars when sanitizing, else 1000).
- Header policy: `SENSITIVE_HEADERS` (authorization, cookie, x-api-key, …) → `***REDACTED***`; `SAFE_HEADERS` allow-list logged; everything else dropped (`:14-82`).
- Body sanitizer `_sanitize_body()` redacts EMAIL / SSN / CARD / **PHONE** / password / token / api_key / authorization (`:85-125`).
- Auto-mounts the dashboard at `config.dashboard_auto_path` if `auto_mount_dashboard` (`:234-241`).

### `mount_dashboard(app, path=None)` (`:244-285`)

Attaches the dashboard via `app.include_router(router, prefix=path, include_in_schema=False)` — **routes, not `app.mount()`** — so it shares the parent's middleware/exception stack, stays out of OpenAPI, and is `root_path`-aware (mirrors FastAPI's own `/docs`).

### `instrument_llm(config)` (`integrations/llm.py:6-89`)

Dynamic `__import__` + `.instrument()` per provider, guarded by allow/block lists (`_should_instrument`, `:17-26`; block-list wins). Providers wired (12): OpenAI, Anthropic, Cohere, Mistral, VertexAI, Bedrock, Replicate, GoogleGenerativeAI (legacy), GoogleGenAI (modern), LangChain, LlamaIndex, Haystack. Missing libs are silently skipped (`ImportError` swallowed).

______________________________________________________________________

## 8. Dashboard (`dashboard/`)

Self-hosted FastAPI UI **and** OTLP/HTTP-JSON receiver. **In-memory only.**

- Store: `TELEMETRY_DATA = {"traces":[], "logs":[], "metrics":[]}`, `MAX_ITEMS = 500` (FIFO, newest-first) (`server.py:17-18`).
- Default standalone: `start_dashboard(port=10108, host="0.0.0.0")` (`server.py:276-278`).

**Access control** (`create_dashboard_router`, `server.py:44-103`):

- If `dashboard_username` **and** `dashboard_password` set → HTTP Basic via `secrets.compare_digest` (`auth_check`).
- Else → `localhost_only`: 403 for non-`127.0.0.1/::1/localhost` unless `dashboard_allow_remote=True`.

**Routes:**

| Method   | Path             | Purpose                                                                    |
| -------- | ---------------- | -------------------------------------------------------------------------- |
| POST     | `/v1/traces`     | OTLP traces in (newest-first, cap 500)                                     |
| POST     | `/v1/logs`       | OTLP logs in                                                               |
| POST     | `/v1/metrics`    | OTLP metrics in                                                            |
| POST     | `/api/ingest`    | combined OTLP (routes by `resourceSpans`/`resourceLogs`/`resourceMetrics`) |
| GET      | `/api/telemetry` | dump current store                                                         |
| GET      | `/{full_path}`   | SPA, with path-traversal guard `_safe_static_file` (`server.py:28-41`)     |
| (router) | `/api/...`       | SDK-docs API (below)                                                       |

`get_dashboard_app()` adds CORS **only** when `dashboard_cors_origins` is set (opt-in; no wildcard) (`server.py:256-266`).

**SDK-docs API** (`dashboard/api.py`, prefix `/api`): `GET /sdk/schema`, `/sdk/schema/json`, `/sdk/schema/markdown`, `/sdk/decorators[/{name}]`, `/sdk/functions[/{name}]`, `/sdk/config`, `/sdk/config/formatted`, `/sdk/examples`, `/sdk/quick-reference`, `/traced/functions`, `/health`.

______________________________________________________________________

## 9. Introspection / registry / schema

- `registry.py` — thread-safe **singleton** `FunctionRegistry` (`__new__` double-checked lock, `:122-129`). Dataclasses `FunctionMetadata`, `DecoratorMetadata`, `ConfigFieldMetadata`. Tracks SDK functions, decorators, config fields, and user `@trace` fns; `to_dict()` serializes everything (`:434-497`). `_make_serializable` coerces dataclasses/callables/sets for JSON (`:143-176`).
- `introspection.py` — builds doc metadata from the registry; **auto-runs on import** (per module map). Feeds the dashboard API.
- `schema.py` — generates an OpenAPI-like SDK schema (`generate_sdk_schema`, `:14-59`) + JSON/Markdown exporters; declares dashboard endpoints (standalone 10108 / mounted `/rouge`) and the fastapi integration.

______________________________________________________________________

## 10. Utilities (`utils/`)

- `config.py` — `find_rouge_config()` walks up/down for `.rouge-config.yaml`.
- `io.py` — folder walking helpers.
- `security.py` — `validate_config_value()`; also (per `issues.md:217`) a Fernet-based credential cache writing `~/.rouge/.key` next to `credentials.enc` (flagged D5: key stored beside ciphertext).

______________________________________________________________________

## 11. Notable gaps / flags (low-level)

- Dashboard storage is in-memory, 500-item cap, non-persistent (`server.py:17-18`) — not durable telemetry.
- `credentials.py` / `CredentialManager` (imported at `tracer.py:30`, `logger.py:14`) exists & imports fine (verified by runtime import) but is hidden from static inspection tools by a local credentials-path guardrail.
- No event/alerting/webhook/outbound-action surface anywhere — telemetry is write-only (collect → export).

______________________________________________________________________

## 12. Canonical usage

```python
import rouge_ai

rouge_ai.init(
    service_name="my-app",
    environment="production",
    otlp_endpoint="https://collector.example.com:4318/v1/traces",
    traces_sampler_ratio=0.25,
    llm_providers=["openai", "anthropic"],   # allow-list
)

@rouge_ai.trace(rouge_ai.TraceOptions(trace_params=True, trace_return_value=True))
def handle(x, y):
    return x + y

log = rouge_ai.get_logger(__name__)
log.info("event")            # correlated to current span; attaches as span event in local mode

# FastAPI
from fastapi import FastAPI
app = FastAPI()
rouge_ai.connect_fastapi(app)          # auto-traces routes + mounts dashboard at /rouge

rouge_ai.shutdown()          # flush on exit
```
