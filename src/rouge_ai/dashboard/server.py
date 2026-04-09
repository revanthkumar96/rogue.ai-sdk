import logging
import os
import secrets

import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rouge-dashboard")

# In-memory storage for telemetry data
# In a production scenario, this could be SQLite or a persistent store
TELEMETRY_DATA = {"traces": [], "logs": [], "metrics": []}
MAX_ITEMS = 500

security = HTTPBasic()

def get_dashboard_app(config=None):
    """
    Creates and returns the Rouge Dashboard FastAPI application.
    
    Args:
        config: Optional RougeConfig object containing security settings.
    """
    
    # Auth dependency
    async def auth_check(credentials: HTTPBasicCredentials = Depends(security)):
        if not config or not config.dashboard_username or not config.dashboard_password:
            # If no auth configured, allow access
            return True
            
        is_correct_username = secrets.compare_digest(
            credentials.username, config.dashboard_username)
        is_correct_password = secrets.compare_digest(
            credentials.password, config.dashboard_password)
        
        if not (is_correct_username and is_correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return True

    # Use dependencies only if configured
    app_dependencies = []
    if config and config.dashboard_username and config.dashboard_password:
        app_dependencies = [Depends(auth_check)]

    app = FastAPI(
        title="Rouge.AI Dashboard",
        dependencies=app_dependencies
    )

    # Enable CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/v1/traces")
    async def collect_traces(request: Request):
        try:
            data = await request.json()
            TELEMETRY_DATA["traces"].insert(0, data)
            TELEMETRY_DATA["traces"] = TELEMETRY_DATA["traces"][:MAX_ITEMS]
            logger.info("Received traces: %d resource spans",
                        len(data.get("resourceSpans", [])))
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error collecting traces: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/ingest")
    async def ingest_telemetry(request: Request):
        try:
            data = await request.json()
            if "resourceSpans" in data:
                TELEMETRY_DATA["traces"].insert(0, data)
                TELEMETRY_DATA["traces"] = TELEMETRY_DATA["traces"][:MAX_ITEMS]
            if "resourceLogs" in data:
                TELEMETRY_DATA["logs"].insert(0, data)
                TELEMETRY_DATA["logs"] = TELEMETRY_DATA["logs"][:MAX_ITEMS]
            if "resourceMetrics" in data:
                TELEMETRY_DATA["metrics"].insert(0, data)
                TELEMETRY_DATA["metrics"] = TELEMETRY_DATA["metrics"][:MAX_ITEMS]

            logger.info("Ingested telemetry from collector")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/v1/logs")
    async def collect_logs(request: Request):
        try:
            data = await request.json()
            TELEMETRY_DATA["logs"].insert(0, data)
            TELEMETRY_DATA["logs"] = TELEMETRY_DATA["logs"][:MAX_ITEMS]
            logger.info(
                f"Received logs: {len(data.get('resourceLogs', []))} resource logs"
            )
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/v1/metrics")
    async def collect_metrics(request: Request):
        try:
            data = await request.json()
            TELEMETRY_DATA["metrics"].insert(0, data)
            TELEMETRY_DATA["metrics"] = TELEMETRY_DATA["metrics"][:MAX_ITEMS]
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.get("/api/telemetry")
    async def get_telemetry():
        return TELEMETRY_DATA

    # Mount SDK documentation API routes
    try:
        from rouge_ai.dashboard.api import create_api_router
        api_router = create_api_router()
        app.include_router(api_router)
        logger.info("SDK documentation API routes mounted successfully")
    except Exception as e:
        logger.warning(f"Failed to mount SDK documentation API routes: {e}")

    # Path to static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    if os.path.exists(static_dir) and os.listdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("v1/"):
                return None

            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)

            if "." not in full_path.split("/")[-1]:
                index_file = os.path.join(static_dir, "index.html")
                if os.path.exists(index_file):
                    return FileResponse(index_file)

            return HTMLResponse("File not found", status_code=404)
    else:
        @app.get("/")
        async def root():
            return {
                "message": "Rouge Dashboard Backend is running",
                "usage": "Send OTLP data to /v1/traces or /v1/logs",
                "status": "Frontend not found"
            }

    return app

# Maintain backward compatibility for standalone launch
app = get_dashboard_app()

def start_dashboard(port: int = 10108, host: str = "0.0.0.0"):
    logger.info(f"Starting Rouge Dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_dashboard()
