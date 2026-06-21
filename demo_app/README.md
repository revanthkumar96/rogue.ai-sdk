# Rouge.AI Demo Application

A single, self-contained FastAPI app that showcases the Rouge.AI SDK end to
end — auto-instrumented routes, a traced helper and a traced streaming
generator, span-correlated logging, and the auto-mounted dashboard. No cloud
account, no AWS credentials, and no external OpenTelemetry collector required.

## Run it

```bash
pip install -e ".[fastapi]"     # from the repo root
python demo_app/main.py
```

Then open:

- **Dashboard** — http://127.0.0.1:8000/rouge (auto-mounted like Swagger's `/docs`)
- **Swagger UI** — http://127.0.0.1:8000/docs
- Try: http://127.0.0.1:8000/summarize?text=hello+world
- Try: http://127.0.0.1:8000/chat?prompt=hi (streaming)

Hit a few endpoints, then watch the traces appear on the dashboard's
**Traces** tab and the SDK reference on **SDK Docs**.

## What it demonstrates

- **Local-first** — `rouge_ai.init(local_mode=True, ...)` exports spans straight
  to the bundled dashboard; nothing leaves your machine.
- **One-line integration** — `rouge_ai.connect_fastapi(app)` auto-instruments
  every route and auto-mounts the dashboard at `/rouge`.
- **`@rouge_ai.trace`** — a traced sync helper (`summarize`) and a traced async
  generator (`stream_tokens`) so both span kinds appear.
- **Correlated logging** — `rouge_ai.get_logger()` attaches log records to the
  active span.
