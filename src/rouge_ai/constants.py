"""Constants and configuration mappings for Rouge"""

DEFAULT_VERIFICATION_ENDPOINT = "https://api.prod1.rouge.ai/v1/verify/credentials"  # noqa: E501

# Environment variable to config field mapping
# Pattern: ROUGE_[CAPITALIZED_CONFIG_FIELD_NAME] -> config_field_name
ENV_VAR_MAPPING = {
    "ROUGE_SERVICE_NAME": "service_name",
    "ROUGE_GITHUB_OWNER": "github_owner",
    "ROUGE_GITHUB_REPO_NAME": "github_repo_name",
    "ROUGE_GITHUB_COMMIT_HASH": "github_commit_hash",
    "ROUGE_TOKEN": "token",
    "ROUGE_NAME": "name",
    "ROUGE_AWS_ACCESS_KEY_ID": "aws_access_key_id",
    "ROUGE_AWS_SECRET_ACCESS_KEY": "aws_secret_access_key",
    "ROUGE_AWS_SESSION_TOKEN": "aws_session_token",
    "ROUGE_AWS_REGION": "aws_region",
    "ROUGE_OTLP_ENDPOINT": "otlp_endpoint",
    "ROUGE_ENVIRONMENT": "environment",
    "ROUGE_ENABLE_SPAN_CONSOLE_EXPORT": "enable_span_console_export",
    "ROUGE_ENABLE_LOG_CONSOLE_EXPORT": "enable_log_console_export",
    "ROUGE_ENABLE_SPAN_CLOUD_EXPORT": "enable_span_cloud_export",
    "ROUGE_ENABLE_LOG_CLOUD_EXPORT": "enable_log_cloud_export",
    "ROUGE_LOCAL_MODE": "local_mode",
    "ROUGE_VERIFICATION_ENDPOINT": "verification_endpoint",
    "ROUGE_TRACER_VERBOSE": "tracer_verbose",
    "ROUGE_LOGGER_VERBOSE": "logger_verbose",
}
