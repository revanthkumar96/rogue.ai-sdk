"""Configuration management for Rouge"""

from dataclasses import dataclass

from rouge_ai.constants import DEFAULT_VERIFICATION_ENDPOINT


@dataclass
class RougeConfig:
    r"""Configuration for Rouge tracing and logging"""
    # Identification
    service_name: str

    # GitHub Identification
    github_owner: str | None = None
    github_repo_name: str | None = None
    github_commit_hash: str | None = None

    # Token for Rouge API
    token: str | None = None

    # User identification
    name: str | None = None

    # AWS Configuration
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    aws_region: str = "us-west-2"

    # OpenTelemetry Configuration
    # SECURITY: Changed to HTTPS
    otlp_endpoint: str = "https://localhost:4318/v1/traces"

    # Environment
    environment: str = "development"

    # Whether to enable console export of spans and logs
    enable_span_console_export: bool = False
    enable_log_console_export: bool = True

    # Whether to enable cloud export of spans and logs
    enable_span_cloud_export: bool = True
    enable_log_cloud_export: bool = True

    # Local mode
    local_mode: bool = False

    # Verification endpoint
    verification_endpoint: str = DEFAULT_VERIFICATION_ENDPOINT

    # Verbose traces for debugging
    tracer_verbose: bool = False

    # Verbose logging for debugging
    logger_verbose: bool = False

    # LLM Instrumentation
    instrument_llm: bool = True
    llm_providers: list[str] | None = None

    # Security Configuration
    allow_insecure_transport: bool = False  # Allow HTTP endpoints explicitly
    # SECURITY: Disabled by default (PII risk)
    log_response_bodies: bool = False
    log_request_bodies: bool = False
    # Sanitize sensitive data in telemetry
    sanitize_telemetry_data: bool = True

    def __post_init__(self):
        self._name = self.name
        self._sub_name = (f"{self.service_name}-"
                          f"{self.environment}")

        # SECURITY: Validate endpoint uses HTTPS unless explicitly allowed
        self._validate_endpoint_security()

    def _validate_endpoint_security(self) -> None:
        """Validate that endpoints use HTTPS for security.

        Raises:
            ValueError: If HTTP endpoint is used without explicit permission
        """
        import sys
        from urllib.parse import urlparse

        endpoints_to_check = [
            ("otlp_endpoint", self.otlp_endpoint),
            ("verification_endpoint", self.verification_endpoint),
        ]

        for endpoint_name, endpoint_url in endpoints_to_check:
            try:
                parsed = urlparse(endpoint_url)

                # SECURITY: Block metadata endpoints to prevent SSRF
                # Check this first before scheme validation
                if parsed.hostname in [
                        "169.254.169.254",  # AWS metadata
                        "metadata.google.internal",  # GCP metadata
                        "metadata",
                ]:
                    raise ValueError(
                        f"Metadata endpoint not allowed for {endpoint_name}: "
                        f"{endpoint_url}")

                # Allow HTTP only for localhost/127.0.0.1 or with explicit flag
                if parsed.scheme == "http":
                    is_localhost = parsed.hostname in [
                        "localhost", "127.0.0.1", "::1"
                    ]

                    if not is_localhost and not self.allow_insecure_transport:
                        msg = (f"Insecure HTTP endpoint detected for "
                               f"{endpoint_name}: {endpoint_url}\n"
                               f"Use HTTPS for security, or set "
                               f"allow_insecure_transport=True to "
                               f"explicitly allow HTTP.")
                        raise ValueError(msg)

                    if not is_localhost and self.allow_insecure_transport:
                        # Warn when using insecure transport
                        msg = (f"[Rouge] WARNING: Using insecure HTTP "
                               f"endpoint for {endpoint_name}: "
                               f"{endpoint_url}")
                        print(msg, file=sys.stderr)

                # Ensure valid scheme
                if parsed.scheme not in ["http", "https"]:
                    raise ValueError(
                        f"Invalid endpoint scheme for {endpoint_name}: "
                        f"{parsed.scheme}. Must be http or https.")

            except ValueError:
                raise
            except Exception as e:
                msg = (f"Invalid endpoint URL for {endpoint_name}: "
                       f"{endpoint_url}. Error: {e}")
                raise ValueError(msg)
