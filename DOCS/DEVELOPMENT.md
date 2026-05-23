# Development

## 本機測試

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

目前主要測試：

- `tests/test_v01_operations.py`：Operations Center rendering、artifact serialization、task list API、audit API。
- `tests/test_v05_auth_rbac.py`：local dev token、RBAC、approval actor、artifact tenant access。
- `tests/test_v06_reliability.py`：idempotency、rate limit、reliability store、worker lock、DLQ replay。
- `tests/test_v10_operations_ui.py`：V1.0 Operations UI。
- `tests/test_v10_auth_jwks.py`：local token 與 JWKS verifier。
- `tests/test_v10_artifacts_s3.py`：S3 artifact store 與 content endpoint。
- `tests/test_v10_dlq_ops.py`：bulk replay 與 quarantine。
- `tests/test_v10_replay.py`：Replay-lite timeline。

## Docker

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

Docker Compose 預設使用：

- PostgreSQL system of record。
- Redis reliability store。
- Kafka task bus。
- MinIO-compatible S3 artifact backend。
- `/operations` 作為可操作 UI 入口。

## Bootstrap

`scripts/bootstrap.py` 會：

- 建立 SQLAlchemy tables。
- Seed local dev tenant/users。
- 確認 S3 bucket 存在。
- 在 `BOOTSTRAP_KAFKA_TOPICS=true` 時建立 Kafka topics。
