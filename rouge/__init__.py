from rouge.logger import get_logger, initialize_logger
from rouge.tracer import init, shutdown, trace

__version__ = '0.0.7'

from rouge.tracer import get_config
if get_config() is None:
    init()
    initialize_logger(get_config())

__all__ = [
    'init',
    'trace',
    'get_logger',
    'shutdown',
]
