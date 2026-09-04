from prometheus_client import Counter, Gauge, Histogram

TASK_CREATED = Counter("browser_agent_tasks_created_total", "Tasks created")
TASK_EXECUTED = Counter("browser_agent_tasks_executed_total", "Tasks executed")
TASK_FAILED = Counter("browser_agent_tasks_failed_total", "Tasks failed")
TASK_DLQ = Counter("browser_agent_tasks_dlq_total", "Tasks moved to DLQ")
TASK_DURATION = Histogram("browser_agent_task_duration_seconds", "Task duration")
HTTP_REQUESTS = Counter(
    "browser_agent_http_requests_total",
    "HTTP requests",
    ["method", "path", "status_code"],
)
HTTP_DURATION = Histogram(
    "browser_agent_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)
AUTH_FAILURES = Counter(
    "browser_agent_auth_failures_total",
    "Authentication failures",
    ["reason"],
)
PRODUCTION_READINESS = Gauge(
    "browser_agent_production_readiness",
    "Production readiness state: 1 ready, 0 degraded, -1 not_ready",
)
