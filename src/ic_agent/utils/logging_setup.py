"""Logging configuration shared across all components."""

import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with a consistent format.

    Safe to call multiple times; subsequent calls just adjust the level.
    """
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return

    logging.basicConfig(level=level.upper(), format=_LOG_FORMAT)
