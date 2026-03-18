from rouge_ai.config import RougeConfig
from rouge_ai.logger import get_logger
from rouge_ai.tracer import TraceOptions, shutdown, trace, get_tracer


def launch_dashboard(port: int = 10108, host: str = "0.0.0.0"):
    """Launch the Rouge.AI self-hosted dashboard.
    
    This starts a FastAPI server on the specified port that collects
    telemetry and provides a beautiful web UI for visualization.
    """
    from rouge_ai.dashboard.server import start_dashboard
    start_dashboard(port=port, host=host)

__version__ = "0.0.10"


def init(**kwargs):
    """Initialize Rouge tracing and logging.

    This is the main entry point for setting up tracing and logging.
    Call this once at the start of your application.

    Args:
        **kwargs: Configuration parameters for RougeConfig.
            If a .rouge-config.yaml file exists, it will be loaded first,
            and any kwargs provided will override the file configuration.

    Returns:
        TracerProvider instance
    """
    from rouge_ai.logger import initialize_logger as _initialize_logger
    from rouge_ai.tracer import init as _init

    # Initialize tracer (this sets the global context)
    provider = _init(**kwargs)

    # Get the resulting config and credential manager
    from rouge_ai.tracer import _credential_manager, get_config
    config = get_config()

    # Initialize logger with the same config
    if config:
        _initialize_logger(config, _credential_manager)

    return provider


__all__ = [
    '__version__',
    'init',
    'trace',
    'get_tracer',
    'get_logger',
    'shutdown',
    'launch_dashboard',
    'RougeConfig',
    'TraceOptions',
]
