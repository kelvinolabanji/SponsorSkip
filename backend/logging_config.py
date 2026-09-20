"""Logging setup shared by the API process."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Send application logs to stderr with a consistent format."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
