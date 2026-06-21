"""Rouge.AI demo launcher — production-like, distributed, local.

Starts TWO services in separate processes so the demo shows real cross-process
distributed tracing through Rouge.AI:

    rouge-gateway (:8000)  — edge API + the dashboard at /rouge
    rouge-agent   (:8100)  — the real Gemini LangGraph multi-agent

The gateway calls the agent over HTTP with W3C tracecontext injected, so a
single trace spans both services. No cloud account, no AWS credentials, no
external OpenTelemetry collector.

Run:
    pip install -e ".[fastapi,llm]" langgraph langchain-google-genai
    # .env: GEMINI_API_KEY=...   (optional GEMINI_MODEL=...)
    python demo_app/main.py
    # open http://127.0.0.1:8000/rouge

See DEMO_SPEC.md and demo_app/README.md for what to look for.
"""

import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def _wait_for(url: str, tries: int = 40) -> bool:
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print(
            "WARNING: no GEMINI_API_KEY/GOOGLE_API_KEY — /agent/run (Gemini) "
            "will fail; every other endpoint (incl. distributed /agent/ping) "
            "still works. Add the key to .env.")

    print("starting rouge-agent (:8100)…")
    agent = subprocess.Popen(
        [sys.executable,
         os.path.join(HERE, "agent_service.py")])
    try:
        if _wait_for("http://127.0.0.1:8100/health"):
            print("rouge-agent is up.")
        else:
            print("WARNING: rouge-agent did not become healthy; /agent/* may "
                  "fail, but the gateway will still start.")
        print("starting rouge-gateway (:8000) — dashboard at /rouge …")
        # Blocks until the gateway (uvicorn) exits.
        subprocess.run([sys.executable, os.path.join(HERE, "gateway.py")])
    finally:
        print("stopping rouge-agent…")
        agent.terminate()
        try:
            agent.wait(timeout=5)
        except Exception:
            agent.kill()


if __name__ == "__main__":
    main()
