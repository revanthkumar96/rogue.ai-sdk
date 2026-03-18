import subprocess
import time
import json
import requests
import os

def run_test():
    print("Stopping any existing OTel collector...")
    subprocess.run(["docker", "stop", "otel-collector"], stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "rm", "otel-collector"], stderr=subprocess.DEVNULL)

    print("Launching Rouge Dashboard on port 10108...")
    dashboard_proc = subprocess.Popen(
        ["uv", "run", "python", "-c", "import rouge_ai; rouge_ai.launch_dashboard()"],
        cwd="c:/Users/sudik/OneDrive/Desktop/Rouge.ai/rouge.ai",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for dashboard to start
    time.sleep(10)
    
    print("Syncing Demo App dependencies...")
    subprocess.run(["uv", "sync"], cwd="c:/Users/sudik/OneDrive/Desktop/Rouge.ai/rouge.ai/demo_app")

    print("Running OTel Collector via Docker...")
    # Use a more Docker-friendly path format for Windows
    config_path = "c:/Users/sudik/OneDrive/Desktop/Rouge.ai/rouge.ai/demo_app/otel-config.yaml"
    subprocess.run([
        "docker", "run", "-d", "--name", "otel-collector",
        "-p", "4317:4317", "-p", "4318:4318",
        "-v", f"{config_path}:/etc/otelcol/config.yaml",
        "otel/opentelemetry-collector:latest"
    ])
    
    print("Waiting for Collector to be ready...")
    for i in range(15):
        time.sleep(2)
        try:
            requests.get("http://127.0.0.1:4318", timeout=1)
            print("Collector is up!")
            break
        except:
            print(".", end="", flush=True)
    print()

    print("Running Demo App...")
    demo_proc = subprocess.run(
        ["uv", "run", "python", "main.py"],
        cwd="c:/Users/sudik/OneDrive/Desktop/Rouge.ai/rouge.ai/demo_app",
        capture_output=True,
        text=True
    )
    
    print("Demo App Output:")
    print(demo_proc.stdout)
    if demo_proc.stderr:
        print("Demo App Errors:")
        print(demo_proc.stderr)
        
    print("Waiting for spans to be exported (batching)...")
    time.sleep(5)
    
    print("Querying Dashboard Telemetry API...")
    try:
        resp = requests.get("http://127.0.0.1:10108/api/telemetry")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Traces received: {len(data['traces'])}")
            print(f"Logs received: {len(data['logs'])}")
            if len(data['traces']) > 0:
                print("SUCCESS: Telemetry captured!")
            else:
                print("FAILURE: Dashboard reachable but no telemetry found.")
                print("Checking Collector Logs...")
                subprocess.run(["docker", "logs", "otel-collector"])
        else:
            print(f"FAILURE: Dashboard API returned status {resp.status_code}")
    except Exception as e:
        print(f"FAILURE: Could not connect to dashboard: {e}")
        print("Checking Dashboard process...")
        if dashboard_proc.poll() is not None:
            print(f"Dashboard process exited with code {dashboard_proc.returncode}")
            out, err = dashboard_proc.communicate()
            print("Dashboard Stdout:", out)
            print("Dashboard Stderr:", err)
    
    print("Cleaning up...")
    dashboard_proc.terminate()

if __name__ == "__main__":
    run_test()
