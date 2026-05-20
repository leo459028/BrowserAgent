# BrowserAgent 文件總覽

更新日期：2026-05-20

本目錄整理 `BrowserAgent` 專案目前的架構、API、資料模型、設定、維運方式、
安全政策、可觀測性、應用場景與 roadmap。文件內容已對齊目前程式碼與本機
Docker Compose 端到端驗證結果。

## 專案定位

`BrowserAgent` 是企業級 Browser Agent 平台的 production-grade scaffold。它提供
FastAPI control plane、PostgreSQL system of record、Kafka event bus、Playwright
worker、policy gate、approval flow、artifact persistence、evaluation、metrics 與
audit trail。

目前完成到 v0.2 completion/stabilization：

- allowlisted low/medium task 會進入 `pending_approval`。
- high/critical risk task 會進入 `pending_approval`，不再永久 `blocked`。
- sensitive instruction 會進入 `pending_approval`。
- blocked-domain task 會進入 `blocked`。
- approval 後 task 會進入 `queued`，由 worker 透過 Kafka 消費並執行。
- `/demo` 已是本機 v0.2 Dashboard，可觀察 tasks、metrics、audit、steps、evaluation 與 artifacts。

## 文件索引

| 文件 | 說明 |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系統架構、runtime components、task lifecycle |
| [API.md](./API.md) | FastAPI endpoints、request/response、Dashboard API |
| [DATA_MODEL.md](./DATA_MODEL.md) | PostgreSQL schema、主要資料表、資料流 |
| [CONFIGURATION.md](./CONFIGURATION.md) | 環境變數、Docker Compose、Kafka topics、artifact 設定 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 本機開發、測試、常用指令 |
| [RUNBOOK.md](./RUNBOOK.md) | Docker Compose 啟動、Dashboard 驗證、常見問題 |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | allowlist、prompt injection、approval policy、安全限制 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | health checks、metrics、logs、audit、Dashboard 觀察 |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已實作與尚未實作功能清單 |
| [ROADMAP.md](./ROADMAP.md) | v0.3 之後的實作方向 |
| [USE_CASES.md](./USE_CASES.md) | 專案主要作用與實際應用場景 |

## 建議閱讀順序

1. 先讀 [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)，確認目前完成度。
2. 再讀 [ARCHITECTURE.md](./ARCHITECTURE.md)，理解 control plane / data plane。
3. 要本機驗證時讀 [RUNBOOK.md](./RUNBOOK.md) 與 [API.md](./API.md)。
4. 要規劃下一版時讀 [ROADMAP.md](./ROADMAP.md) 與 [USE_CASES.md](./USE_CASES.md)。

## 目前注意事項

- API 仍使用固定 demo tenant/user UUID，正式 auth/RBAC 放在 v0.5。
- Docker Compose 已包含 MinIO，但目前 artifact store 仍寫入本地 volume。
- `/metrics` 是 process-local；在 Docker Compose 多 process 架構下，API endpoint 不會自動匯總 worker process 的 metrics。
- `MAX_TASK_RETRIES` 與 `TASK_TIMEOUT_SECONDS` 已在 Settings 定義，但 worker retry 目前仍是 hardcoded minimal implementation。
- `scripts/bootstrap.py` 是建立 schema、seed demo identity 與 Kafka topics 的主要路徑。

