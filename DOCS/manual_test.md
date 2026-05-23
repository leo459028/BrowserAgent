# V1.0 Operations Center Manual Test

本文件說明如何手動驗證 BrowserAgent V1.0 Operations Center。

## 啟動

```powershell
docker compose up -d --build
```

開啟：

```text
http://127.0.0.1:8000/operations
```

## 最小合格檢查

- 頁面顯示 `Browser Agent v1.0 Operations Center`。
- `Operations Readiness` 可載入。
- `Artifact Backend` 在 Docker Compose 顯示 `s3`。
- `Identity / RBAC` 可切換角色。
- `Try operator create` 顯示 `403`。
- `Normal planner task` 可建立、核准、完成。
- Artifacts 可預覽或通過 access check。
- `Replay Timeline` 顯示 task lifecycle 資訊。
- `Refresh DLQ` 可查 failed tasks。
- `Bulk DLQ replay` 可操作 non-quarantined tasks。

## API 快速檢查

```powershell
$operator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"operator"}'

Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/ops/readiness `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```
