import logging
import os
import secrets

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rouge-dashboard")

# In-memory storage for telemetry data
# In a production scenario, this could be SQLite or a persistent store
TELEMETRY_DATA = {"traces": [], "logs": [], "metrics": []}
MAX_ITEMS = 500

security = HTTPBasic()


def _static_dir() -> str:
    """Absolute path to the built frontend static directory."""
    return os.path.join(os.path.dirname(__file__), "static")


def _safe_static_file(static_dir: str, rel_path: str) -> str | None:
    """Resolve ``rel_path`` under ``static_dir``, guarding against traversal.

    Returns the absolute file path if it is a real file located inside
    ``static_dir``, otherwise None.
    """
    static_root = os.path.realpath(static_dir)
    candidate = os.path.realpath(os.path.join(static_root, rel_path))
    # Ensure the resolved path stays within the static root
    if os.path.commonpath([static_root, candidate]) != static_root:
        return None
    if os.path.isfile(candidate):
        return candidate
    return None


def create_dashboard_router(config=None) -> APIRouter:
    """Create the Rouge dashboard as a FastAPI ``APIRouter``.

    The router bundles telemetry ingestion endpoints, the SDK-documentation
    API, and the single-page-app frontend. It is designed to be attached to
    an existing application via ``app.include_router(router, prefix=...)`` so
    the dashboard behaves like FastAPI's own ``/docs`` (normal routes, shared
    middleware/exception handlers, ``root_path`` aware) instead of a mounted
    sub-application.

    Args:
        config: Optional RougeConfig providing dashboard security settings.

    Returns:
        Configured APIRouter. The caller supplies the mount ``prefix`` and
        ``include_in_schema=False`` at ``include_router`` time.
    """

    # pattern: fastapi@0.137.2 applications.py:1104-1157 (docs as routes,
    # guarded + include_in_schema=False) — adapted to an APIRouter so the
    # whole dashboard can be attached to a user's app without app.mount().

    # Access control. When HTTP Basic credentials are configured we enforce
    # them (covers local + remote). Otherwise the dashboard exposes telemetry
    # and SDK internals, so we restrict it to localhost unless the operator
    # explicitly opts into unauthenticated remote access.
    async def auth_check(
            credentials: HTTPBasicCredentials = Depends(security)):
        is_correct_username = secrets.compare_digest(credentials.username,
                                                     config.dashboard_username)
        is_correct_password = secrets.compare_digest(credentials.password,
                                                     config.dashboard_password)

        if not (is_correct_username and is_correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        return True

    async def localhost_only(request: Request):
        client_host = request.client.host if request.client else None
        is_local = client_host in ("127.0.0.1", "::1", "localhost")
        if is_local or (config and config.dashboard_allow_remote):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("Rouge dashboard is restricted to localhost. Configure "
                    "dashboard_username/password for authenticated remote "
                    "access, or set dashboard_allow_remote=True to allow "
                    "unauthenticated remote access."),
        )

    if config and config.dashboard_username and config.dashboard_password:
        router_dependencies = [Depends(auth_check)]
    else:
        router_dependencies = [Depends(localhost_only)]

    router = APIRouter(dependencies=router_dependencies)

    # --- Telemetry ingestion (OTLP/HTTP JSON receivers) --------------------

    @router.post("/v1/traces")
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
            return JSONResponse({
                "status": "error",
                "message": str(e)
            },
                                status_code=400)

    @router.post("/api/ingest")
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
                TELEMETRY_DATA["metrics"] = TELEMETRY_DATA[
                    "metrics"][:MAX_ITEMS]

            logger.info("Ingested telemetry from collector")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            return JSONResponse({
                "status": "error",
                "message": str(e)
            },
                                status_code=400)

    @router.post("/v1/logs")
    async def collect_logs(request: Request):
        try:
            data = await request.json()
            TELEMETRY_DATA["logs"].insert(0, data)
            TELEMETRY_DATA["logs"] = TELEMETRY_DATA["logs"][:MAX_ITEMS]
            logger.info(f"Received logs: {len(data.get('resourceLogs', []))} "
                        f"resource logs")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            return JSONResponse({
                "status": "error",
                "message": str(e)
            },
                                status_code=400)

    @router.post("/v1/metrics")
    async def collect_metrics(request: Request):
        try:
            data = await request.json()
            TELEMETRY_DATA["metrics"].insert(0, data)
            TELEMETRY_DATA["metrics"] = TELEMETRY_DATA["metrics"][:MAX_ITEMS]
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return JSONResponse({
                "status": "error",
                "message": str(e)
            },
                                status_code=400)

    @router.get("/api/telemetry")
    async def get_telemetry():
        return TELEMETRY_DATA

    # --- SDK documentation API --------------------------------------------
    # Mounted as a nested router (kept before the SPA fallback so its routes
    # win over the catch-all).
    try:
        from rouge_ai.dashboard.api import create_api_router
        router.include_router(create_api_router())
        logger.info("SDK documentation API routes mounted successfully")
    except Exception as e:
        logger.warning(f"Failed to mount SDK documentation API routes: {e}")

    # --- Frontend (single-page app) ---------------------------------------
    # Served via routes returning FileResponse. The build uses relative asset
    # paths (Vite base "./"), so serving the shell at "{prefix}/" makes the
    # browser resolve "./assets/..." under the prefix without a StaticFiles
    # mount. The catch-all is registered LAST so it never shadows the API
    # routes above.
    static_dir = _static_dir()
    has_frontend = os.path.isdir(static_dir) and bool(os.listdir(static_dir))

    if has_frontend:

        @router.get("/")
        async def serve_index():
            index_file = os.path.join(static_dir, "index.html")
            if os.path.isfile(index_file):
                return FileResponse(index_file)
            return HTMLResponse("Dashboard frontend not found",
                                status_code=404)

        @router.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            # Serve a real static asset if it exists (e.g. assets/*.js,
            # favicon.svg); otherwise fall back to index.html for client-side
            # routing. Extensioned paths that don't exist are a real 404.
            static_file = _safe_static_file(static_dir, full_path)
            if static_file is not None:
                return FileResponse(static_file)

            if "." not in os.path.basename(full_path):
                index_file = os.path.join(static_dir, "index.html")
                if os.path.isfile(index_file):
                    return FileResponse(index_file)

            return HTMLResponse("File not found", status_code=404)
    else:

        @router.get("/")
        async def root():
            return {
                "message": "Rouge Dashboard Backend is running",
                "usage": "Send OTLP data to /v1/traces or /v1/logs",
                "status": "Frontend not found"
            }

    return router


def get_dashboard_app(config=None) -> FastAPI:
    """Create a standalone FastAPI app hosting the dashboard.

    Used by :func:`launch_dashboard` / :func:`start_dashboard` to run the
    dashboard as its own server. Applications that already have a FastAPI app
    should instead attach the dashboard with
    ``app.include_router(create_dashboard_router(config), prefix="/rouge",
    include_in_schema=False)`` — see ``rouge_ai.mount_dashboard``.

    Args:
        config: Optional RougeConfig object containing security settings.
    """
    app = FastAPI(title="Rouge.AI Dashboard")

    # CORS is opt-in: only enable it when origins are explicitly configured.
    # The dashboard SPA is served same-origin and needs no CORS; defaulting to
    # "*" would expose the API cross-origin.
    cors_origins = config.dashboard_cors_origins if config else None
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(create_dashboard_router(config=config))
    return app


# Maintain backward compatibility for standalone launch
app = get_dashboard_app()


def start_dashboard(port: int = 10108, host: str = "0.0.0.0"):
    logger.info(f"Starting Rouge Dashboard on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_dashboard()
