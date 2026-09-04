import logging
import sys
from pythonjsonlogger import jsonlogger

def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s "
        "%(correlation_id)s %(trace_id)s %(span_id)s %(parent_span_id)s %(request_id)s "
        "%(task_id)s %(tenant_id)s %(actor_email)s %(event_name)s "
        "%(service_name)s %(service_version)s %(environment)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
