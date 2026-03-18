import os
import json
import logging
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rouge-dashboard")

app = FastAPI(title="Rouge.AI Dashboard")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for telemetry data
# In a production scenario, this could be SQLite or a persistent store
TELEMETRY_DATA = {
    "traces": [],
    "logs": [],
    "metrics": []
}

MAX_ITEMS = 500

@app.post("/v1/traces")
async def collect_traces(request: Request):
    try:
        data = await request.json()
        TELEMETRY_DATA["traces"].insert(0, data)
        # Prune older items
        TELEMETRY_DATA["traces"] = TELEMETRY_DATA["traces"][:MAX_ITEMS]
        logger.info(f"Received traces: {len(data.get('resourceSpans', []))} resource spans")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error collecting traces: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/v1/logs")
async def collect_logs(request: Request):
    try:
        data = await request.json()
        TELEMETRY_DATA["logs"].insert(0, data)
        TELEMETRY_DATA["logs"] = TELEMETRY_DATA["logs"][:MAX_ITEMS]
        logger.info(f"Received logs: {len(data.get('resourceLogs', []))} resource logs")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error collecting logs: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/v1/metrics")
async def collect_metrics(request: Request):
    try:
        data = await request.json()
        TELEMETRY_DATA["metrics"].insert(0, data)
        TELEMETRY_DATA["metrics"] = TELEMETRY_DATA["metrics"][:MAX_ITEMS]
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/telemetry")
async def get_telemetry():
    """Endpoint for the frontend to fetch latest data"""
    return TELEMETRY_DATA

# Path to static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Mount static files if directory exists
if os.path.exists(STATIC_DIR) and os.listdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for all non-API paths (SPA support)
        if full_path.startswith("api/") or full_path.startswith("v1/"):
            return None # Should be handled by other routes
        
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return HTMLResponse("Frontend not built. Please run build process.")
else:
    @app.get("/")
    async def root():
        return {
            "message": "Rouge Dashboard Backend is running on port 10108",
            "usage": "Send OTLP data to /v1/traces or /v1/logs",
            "status": "Frontend not found in src/rouge_ai/dashboard/static"
        }

def start_dashboard(port: int = 10108, host: str = "0.0.0.0"):
    logger.info(f"Starting Rouge Dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_dashboard()
