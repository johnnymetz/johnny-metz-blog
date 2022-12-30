import logging
import time
from contextlib import ContextDecorator


class timer(ContextDecorator):  # noqa
    """Context manager and decorator to measure execution time in seconds."""

    def __init__(
        self,
        target_logger: logging.Logger,
        *,
        level=logging.DEBUG,
        name: str | None = None,
        decimals: int = 0,
        threshold: float = 0,
    ):
        """
        :param target_logger: logger to use
        :param level: logging level to use
        :param name: timer name; defaults to function name if used as a decorator
        :param decimals: number of decimals to round to
        :param threshold: only log if execution time is greater than this threshold
        """
        self._logger = target_logger
        self.level = level
        self.name = name
        self.decimals = decimals
        self.threshold = threshold

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
        if net_time >= self.threshold:
            self._logger.log(
                self.level,
                f"{self.name or 'Code'} ran in {net_time:.{self.decimals}f} seconds",
            )
        return False
