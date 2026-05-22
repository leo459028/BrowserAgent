from prometheus_client import Counter, Histogram

TASK_CREATED = Counter("browser_agent_tasks_created_total", "Tasks created")
TASK_EXECUTED = Counter("browser_agent_tasks_executed_total", "Tasks executed")
TASK_FAILED = Counter("browser_agent_tasks_failed_total", "Tasks failed")
TASK_DLQ = Counter("browser_agent_tasks_dlq_total", "Tasks moved to DLQ")
TASK_DURATION = Histogram("browser_agent_task_duration_seconds", "Task duration")
