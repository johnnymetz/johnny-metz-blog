import logging
import time
from contextlib import ContextDecorator

logger = logging.getLogger(__name__)


class timer(ContextDecorator):  # noqa
    """
    Context manager and wrapper to measure execution time in seconds and
    write it to the django logger and, optionally, as a prometheus metric.
    """

    def __init__(self, name: str | None = None, *, decimals=1):
        self.name = name
        self.decimals = decimals

    def __call__(self, func):
        # use decorated function's name if no name is provided
        if not self.name:
            self.name = func.__qualname__

        return super().__call__(func)

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *exc):
        net_time = time.perf_counter() - self.start_time
        logger.info(f"{self.name} ran in {net_time:.{self.decimals}f} seconds")
        return False
