import os
from pathlib import Path

import structlog
from structlog.processors import CallsiteParameter
from structlog.typing import EventDict, FilteringBoundLogger


def format_pathname(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Format the pathname in the event dictionary to be relative to the current working directory.

    e.g. instead of
    /home/user/project/src/backend/app/logging.py:42
    it will be
    src/backend/app/logging.py:42
    """
    if "pathname" not in event_dict:
        return event_dict

    relative_path = os.path.relpath(
        event_dict["pathname"],
        start=Path.cwd(),
    )
    event_dict["pathname"] = f"{relative_path}:{event_dict['lineno']}"
    del event_dict["lineno"]
    del event_dict["func_name"]

    return event_dict


def dev_processors():
    """Return the processors for human-readable console output."""
    return [
        format_pathname,
        structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.RichTracebackFormatter(
                # show_locals=False prevents stack traces longer than max console output.
                show_locals=False,
            ),
        ),
    ]


def create_logger(
    debug: bool = False, log_level: str = "INFO"
) -> FilteringBoundLogger:
    """Create a logger with the given name and level."""
    base_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
        ),
        structlog.processors.CallsiteParameterAdder(
            parameters={
                CallsiteParameter.PATHNAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            }
        ),
    ]

    # JSON log by default, human readable when DEBUG is set
    processors = base_processors + (
        dev_processors()
        if debug
        else [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

    return structlog.get_logger().bind()
