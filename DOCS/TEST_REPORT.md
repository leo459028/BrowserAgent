# Test Report

最後更新：2026-05-20

## 摘要

本報告涵蓋目前 v0.2 與 v0.3 的驗證狀態。

最新完整驗證結果：

- Host unit/integration tests：`pytest -q` -> `24 passed`
- Compile check：`python -m compileall src tests worker alembic` -> passed
- Whitespace check：`git diff --check` -> passed
- Docker test suite：`docker compose exec -T api pytest -q` -> `24 passed`
- Docker E2E browser-agent flow：passed
- Dashboard v0.3 browser verification：passed

## v0.2 Test Coverage

### 測試檔案

- `tests/test_policy.py`
- `tests/test_evaluator.py`
- `tests/test_v01_demo.py`
- `tests/test_v02_lifecycle.py`
- `tests/test_worker_runner.py`

### 覆蓋情境

- Domain allowlist 會阻擋非 allowlisted domain。
- Evaluator 在 final URL、HTML、artifact、expected domain 都符合時回傳 pass。
- Demo approval 會把 actor UUID 記錄在 task，並把 display label 記錄在 approval row。
- Artifact summary serialization 會透過 task detail 回傳。
- Artifact path traversal 若超出 `ARTIFACT_BASE_PATH` 會被拒絕。
- `/demo` 可以正確 render Dashboard。
- `GET /v1/tasks` 會回傳 recent task summaries。
- `GET /v1/tasks/{task_id}/audit` 會回傳 lifecycle events。
- Allowlisted task 會進入 `pending_approval`，並 publish correlation ID。
- Blocked-domain task 會維持 `blocked`，並記錄 created/blocked audit。
- High-risk task 需要 approval。
- Sensitive instruction task 需要 approval。
- Approval 會把 pending task 移到 `queued`。
- Approval 會拒絕不可 approval 的 status。
- Failed task 會記錄 error metadata 與 audit。
- Worker retry 可在 transient failure 後成功。
- Worker 會在最後一次 retry 失敗後 mark failed。
- Worker task ID coercion 支援 UUID 與 UUID string。

## v0.3 Test Coverage

### 測試檔案

- `tests/test_v03_artifacts.py`
- `tests/test_v01_demo.py` 中更新的 v0.3 assertions

### 覆蓋情境

- `LocalArtifactStore` 會回傳 governance metadata：backend、SHA-256、content type、size、retention、redaction status。
- Artifact serialization 會暴露 v0.3 fields：`content_type`、`size_bytes`、`backend`、`redaction_status`、`download_url`。
- Artifact access 遇到 tenant mismatch 會回傳 `403 artifact tenant mismatch`。
- Artifact access 允許 matching tenant。
- Artifact audit payload shape 包含 content type、size、backend、redaction metadata。
- `/demo` 會 render `Browser Agent v0.3 Dashboard`。
- Dashboard HTML 包含 `Artifact Query` 與 `redaction status`。

## Docker E2E Verification

執行過的 commands：

```powershell
docker compose up -d --build api worker
docker compose exec -T api pytest -q
```

Service checks：

- `docker compose ps` 顯示 API、worker、Postgres、Redis、Kafka、Zookeeper、MinIO 都在 running。
- `/healthz` 回傳 `200`。
- `/readyz` 回傳 `200`。
- `/demo` 回傳 `200`，內容包含 `Browser Agent v0.3 Dashboard` 與 `Artifact Query`。

E2E task：

- 建立 task：`v0.3 Docker artifact verification`
- Initial status：`pending_approval`
- Approved status：`queued`
- Final status：`completed`
- Evaluation：`score=100`、`verdict=pass`
- Artifacts produced：2 個，分別是 `screenshot` 與 `html`

Artifact results：

- Screenshot content endpoint 回傳 `200 image/png`。
- HTML content endpoint 回傳 `200 text/html; charset=utf-8`。
- Screenshot metadata 包含 `size_bytes=18002`、`backend=local`、`redaction_status=not_applied`。
- HTML metadata 包含 `size_bytes=528`、`backend=local`、`redaction_status=not_applied`。

Policy regression：

- 建立 blocked-domain task：`v0.3 blocked domain verification`
- Final status：`blocked`

Audit verification：

成功 task 具備以下 expected actions：

```text
task.created
task.pending_approval
task.approved
task.queued
task.execution_started
task.artifact_written
task.artifact_written
task.evaluated
task.completed
```

Metrics verification：

- `/metrics` 包含 `browser_agent_tasks_created_total`。
- `/metrics` 包含 `browser_agent_task_duration_seconds`。

Dashboard verification：

- Browser 載入 `http://127.0.0.1:8000/demo`。
- Dashboard 顯示 v0.3 E2E task。
- Artifact table 顯示 screenshot/html rows 與 governance fields。
- Artifact Query 的 `Check access` 回傳 `Access OK - image/png`。

## 備註

- Docker verification 期間，本機曾有另一個 uvicorn process 綁定 `127.0.0.1:8000`，導致第一次 artifact content check 打到錯誤的 API process，回傳 `403 outside artifact storage`。停止本機 process 後，Docker endpoint 正常回傳 `200`。
- MinIO 在 Docker Compose 中有啟動，但目前 active artifact backend 仍是 local filesystem。
- Metrics 是 process-local，目前不會跨 API 與 worker 聚合。
