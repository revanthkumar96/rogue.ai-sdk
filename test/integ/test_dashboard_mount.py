"""Integration tests for FastAPI-idiomatic dashboard mounting (issue C1).

The dashboard must attach to the user's app as normal routes
(``include_router`` with ``include_in_schema=False``), NOT as a mounted
sub-``FastAPI()`` application. This mirrors how FastAPI itself wires up
``/docs`` (see ``fastapi.applications.FastAPI.setup``), so the dashboard
shares the parent app's middleware/exception handlers, stays out of the
user's OpenAPI schema, and respects ``root_path``.
"""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount

import rouge_ai
import rouge_ai.tracer
from rouge_ai import connect_fastapi, init, mount_dashboard, shutdown


def _init_local(**overrides):
    """Initialize rouge_ai fully offline (no cloud export / credentials)."""
    params = dict(
        service_name="test-dashboard",
        local_mode=True,
        enable_span_cloud_export=False,
        enable_log_cloud_export=False,
    )
    params.update(overrides)
    return init(**params)


def _client(app):
    """TestClient simulating a localhost client (dashboard is localhost-gated
    by default when no auth is configured)."""
    return TestClient(app, client=("127.0.0.1", 50000))


class TestDashboardMount(unittest.TestCase):
    """Validate the dashboard is mounted the FastAPI-idiomatic way."""

    def setUp(self):
        rouge_ai.tracer._tracer_provider = None
        rouge_ai.tracer._config = None
        shutdown()

    def tearDown(self):
        shutdown()

    def test_mount_does_not_use_sub_fastapi_app(self):
        """C1: dashboard must not be a mounted sub-``FastAPI()`` app."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")

        mounted_apps = [
            r for r in app.router.routes
            if isinstance(r, Mount) and isinstance(r.app, FastAPI)
        ]
        self.assertEqual(
            mounted_apps,
            [],
            "Dashboard must be added as routes on the parent app, "
            "not a mounted sub-FastAPI() application",
        )

    def test_dashboard_api_reachable_on_parent_app(self):
        """SDK-docs API answers under the mount prefix on the parent app."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")
        client = _client(app)

        health = client.get("/rouge/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json().get("status"), "healthy")

        schema = client.get("/rouge/api/sdk/schema")
        self.assertEqual(schema.status_code, 200)

    def test_dashboard_excluded_from_parent_openapi(self):
        """include_in_schema=False: dashboard must not pollute user OpenAPI."""
        app = FastAPI()

        @app.get("/users")
        def users():
            return []

        _init_local()
        mount_dashboard(app, path="/rouge")
        client = _client(app)

        spec = client.get("/openapi.json").json()
        rouge_paths = [p for p in spec["paths"] if p.startswith("/rouge")]
        self.assertEqual(rouge_paths, [],
                         f"dashboard leaked into OpenAPI: {rouge_paths}")
        self.assertIn("/users", spec["paths"])  # user's own routes survive

    def test_spa_shell_served_at_prefix_root(self):
        """The SPA shell is served at ``{prefix}/`` (relative asset base)."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")
        client = _client(app)

        resp = client.get("/rouge/", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("root", resp.text)  # <div id="root"></div>

    def test_connect_fastapi_auto_mounts(self):
        """connect_fastapi auto-mounts the dashboard when enabled."""
        app = FastAPI()
        _init_local(auto_mount_dashboard=True, dashboard_auto_path="/rouge")
        connect_fastapi(app)
        client = _client(app)
        self.assertEqual(client.get("/rouge/api/health").status_code, 200)

    def test_auto_mount_can_be_disabled(self):
        """auto_mount_dashboard=False leaves no dashboard routes."""
        app = FastAPI()
        _init_local(auto_mount_dashboard=False)
        connect_fastapi(app)
        client = _client(app)
        self.assertEqual(client.get("/rouge/api/health").status_code, 404)

    def test_dashboard_is_self_contained_build_free_html(self):
        """C3: the UI is a single bundled HTML file, no React build bundle."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")
        client = _client(app)

        resp = client.get("/rouge/", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        body = resp.text
        self.assertIn("<html", body.lower())
        # Inline app (no separate JS to load) ...
        self.assertIn("fetch(", body)
        # ... and crucially NOT a hashed React/Vite bundle or a CDN script.
        self.assertNotIn("assets/index-", body)
        self.assertNotIn("cdn.jsdelivr", body)

    def test_old_react_bundle_is_not_served(self):
        """C3: the previously-shipped Vite bundle must be gone (404)."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")
        client = _client(app)
        resp = client.get("/rouge/assets/index-DjEV-ine.js")
        self.assertEqual(resp.status_code, 404)

    # --- D1: access control -----------------------------------------------

    def test_remote_request_denied_without_auth(self):
        """D1: non-localhost access is denied when no auth is configured."""
        app = FastAPI()
        _init_local()
        mount_dashboard(app, path="/rouge")
        remote = TestClient(app, client=("203.0.113.5", 1234))
        self.assertEqual(remote.get("/rouge/api/health").status_code, 403)

    def test_remote_allowed_with_allow_remote_flag(self):
        """D1: dashboard_allow_remote opts into remote access (no auth)."""
        app = FastAPI()
        _init_local(dashboard_allow_remote=True)
        mount_dashboard(app, path="/rouge")
        remote = TestClient(app, client=("203.0.113.5", 1234))
        self.assertEqual(remote.get("/rouge/api/health").status_code, 200)

    def test_basic_auth_enforced_when_configured(self):
        """D1: with credentials, requests require valid HTTP Basic auth."""
        app = FastAPI()
        _init_local(dashboard_username="admin", dashboard_password="secret")
        mount_dashboard(app, path="/rouge")
        remote = TestClient(app, client=("203.0.113.5", 1234))
        self.assertEqual(remote.get("/rouge/api/health").status_code, 401)
        ok = remote.get("/rouge/api/health", auth=("admin", "secret"))
        self.assertEqual(ok.status_code, 200)

    # --- D2: CORS is not "*" by default -----------------------------------

    def test_standalone_app_has_no_cors_by_default(self):
        """D2: standalone dashboard adds no CORS middleware by default."""
        from starlette.middleware.cors import CORSMiddleware

        from rouge_ai.dashboard.server import get_dashboard_app
        _init_local()
        app = get_dashboard_app(rouge_ai.tracer.get_config())
        self.assertNotIn(CORSMiddleware, [m.cls for m in app.user_middleware])

    def test_standalone_app_cors_when_configured(self):
        """D2: CORS is added only when dashboard_cors_origins is set."""
        from starlette.middleware.cors import CORSMiddleware

        from rouge_ai.dashboard.server import get_dashboard_app
        _init_local(dashboard_cors_origins=["http://example.com"])
        app = get_dashboard_app(rouge_ai.tracer.get_config())
        self.assertIn(CORSMiddleware, [m.cls for m in app.user_middleware])


if __name__ == "__main__":
    unittest.main()
