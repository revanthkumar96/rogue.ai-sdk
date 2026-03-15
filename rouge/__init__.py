from rouge.logger import get_logger
from rouge.tracer import shutdown, trace


def init(**kwargs):
    """Initialize both tracing and logging"""
    from rouge.logger import initialize_logger as _initialize_logger
    from rouge.tracer import init as _init

    # Initialize tracer (this sets the global context)
    provider = _init(**kwargs)

    # Get the resulting config and credential manager
    from rouge.tracer import _credential_manager, get_config
    config = get_config()

    # Initialize logger with the same config
    if config:
        _initialize_logger(config, _credential_manager)

    return provider


__all__ = [
    'init',
    'trace',
    'get_logger',
    'shutdown',
]
