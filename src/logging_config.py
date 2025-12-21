import logging
import sys
import structlog
from typing import Optional

from .config import settings

def configure_logging(log_level: Optional[str] = None):
    """
    Configure structured logging for the application.
    """
    level_name = log_level or settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Simple heuristic: If running in container or explicitly set, use JSON
    # For this environment, we default to Console for readability unless "json" specified
    # Assuming minimal settings object for now, defaulting to False if attribute missing
    use_json = getattr(settings, "log_format", "console") == "json"

    if use_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.PositionalArgumentsFormatter(),
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    # Configure standard library handler to use structlog formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # update root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    
    # Clean up existing handlers (prevent duplicates)
    for h in root_logger.handlers[:-1]: 
        root_logger.removeHandler(h)

    # Specific library noise reduction
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = structlog.get_logger()
    logger.info("logging_configured", level=level_name, mode="json" if use_json else "console")

def get_logger(name: str = None):
    """Get a structured logger."""
    return structlog.get_logger(name)
