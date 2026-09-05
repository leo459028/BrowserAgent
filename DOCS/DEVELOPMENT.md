# Development

## 本機測試

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

目前主要測試（共 18 個測試模組，96 個測試全部通過）：

- `tests/test_v01_operations.py`：Operations Center rendering、artifact serialization、task list API、audit API。
- `tests/test_v05_auth_rbac.py`：local dev token、RBAC、approval actor、artifact tenant access。
- `tests/test_v06_reliability.py`：idempotency、rate limit、reliability store、worker lock、DLQ replay。
- `tests/test_v10_operations_ui.py`：V1.0 Operations UI。
- `tests/test_v10_auth_jwks.py`：local token 與 JWKS verifier。
- `tests/test_v10_artifacts_s3.py`：S3 artifact store 與 content endpoint。
- `tests/test_v10_dlq_ops.py`：bulk replay 與 quarantine。
- `tests/test_v10_replay.py`：Replay-lite timeline。
- `tests/test_v11_tracing.py`：W3C traceparent、Tracer / Span 生命週期、記憶體環形 TraceBuffer 與端到端追蹤端點。
- `tests/test_v11_alerts_webhook.py`：7 大維運告警規則即時評估、外部 Webhook 非阻塞轉發與 Admin 測試派發。
- `tests/test_v11_visual_replay.py`：步驟分頁資料結構、DOM 摘要、截圖關聯、Trace ID 與向後相容 Replay API。
- `tests/test_v11_operations_ui.py`：V1.1 Operations UI 渲染（Alert Badge、Alerting Center、Trace Inspector、Visual Step Replay 分頁條）。
- `tests/test_v12_scheduler.py`：標準 5 欄位 Cron 解析、Redis 分散式搶鎖、防重入調度原則（skip/allow）與任務派發。
- `tests/test_v12_session_vault.py`：Playwright storage_state 憑證序列化、多租戶隔離、跨任務自動注入與一鍵撤銷保護。
- `tests/test_v12_video_artifact.py`：Playwright 全行程 WebM 視訊錄影產生、ArtifactStore 寫入與 Task Replay URL 解析。
- `tests/test_v12_otlp_exporter.py`：非同步背景 Batch Span Exporter、隊列丟棄保護、批次組裝與即時狀態監控。
- `tests/test_v12_apis.py`：Scheduled Tasks CRUD/Trigger、Session Vault 查詢與撤銷、Video 串流播放、Readiness K8s/OTLP 擴充與 V1.2 UI 渲染。
- `tests/test_v13_features.py`：KMS 信封加密（Local/AWS/Vault）、AES-256-GCM 租戶 AAD 防篡改、主金鑰輪換、啟發式選擇器自癒（三級 Fallback Cascade、相似度比對與低信心度拒絕）、多優先權加權佇列分流（High/Queued/Batch）、WebSocket 即時畫面幀推播、線上 Abort 攔截、OIDC PKCE 授權碼交換與 HttpOnly Cookie、Session 解密校驗 API、Helm 3 Chart 結構與全向後相容。

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
