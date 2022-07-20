import logging
from logging import Logger
from typing import Callable
from datetime import datetime
logging_enabled = False


class LoggerManager:
    """Manages loggers of the entire sdk."""

    @staticmethod
    def use_logging():
        """Enables using Logging logger with extended log levels for debugging instead of
        print functions. Note that Logging configuration is performed by the user."""
        global logging_enabled
        logging_enabled = True

    @staticmethod
    def get_logger(category):
        """Creates a new logger for specified category.

        Args:
            category: Logger category.

        Returns:
            Created logger.
        """
        if logging_enabled:
            logger = logging.getLogger(category)
            original_log = logger._log

            def logging_func(level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
                if isinstance(msg, Callable):
                    msg = msg()
                original_log(level, msg, args, exc_info, extra, stack_info, stacklevel)
            logger._log = logging_func
            return logger
        else:
            return NativeLogger(category)


class NativeLogger(Logger):
    """Native logger that uses print function."""

    def debug(self, msg, *args, **kwargs):
        # this logger does not print debug messages
        pass

    def info(self, msg, *args, **kwargs):
        self._log('log', msg, args)

    def warning(self, msg, *args, **kwargs):
        self._log('warn', msg, args)

    def error(self, msg, *args, **kwargs):
        self._log('error', msg, args)

    def exception(self, msg, *args, **kwargs):
        self._log('error', msg, args)

    def _log(self, level: str, msg, args, exc_info=None, extra=None, stack_info: bool = None,
             stacklevel: int = None) -> None:
        if isinstance(msg, Callable):
            msg = msg()
        print(f'[{datetime.now().isoformat()}] {msg}', *args)
