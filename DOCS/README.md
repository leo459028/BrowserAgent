# Browser Agent 專案文件索引

更新日期：2026-05-15

本目錄整理目前 `BrowserAgent` 專案的架構、執行方式、維運 runbook、API、資料模型、治理邊界與 roadmap。文件依據目前 repo 內容建立，並刻意區分「已實作」、「部分實作」與「尚未實作」。

## 專案定位

`BrowserAgent` 是一個企業級 Browser Agent 平台 scaffold。它以 FastAPI 作為 control plane，PostgreSQL 作為 system of record，Kafka 作為事件匯流排，worker 透過 Playwright 執行受控瀏覽器任務，並用 evaluator 對執行結果評分。

目前 repo 更接近可驗證的後端骨架與本機 compose demo，而不是完整 production 產品。已包含任務 API、SkillHub、policy gate、Kafka worker、Playwright runner、artifact 本地寫入、SQL schema、Alembic migration skeleton 與少量單元測試。

## 文件地圖

| 文件 | 用途 |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系統架構、模組責任、事件流程與目前限制 |
| [API.md](./API.md) | FastAPI 端點、request/response 與 curl 範例 |
| [DATA_MODEL.md](./DATA_MODEL.md) | PostgreSQL schema、資料關係與狀態欄位 |
| [CONFIGURATION.md](./CONFIGURATION.md) | 環境變數、Docker Compose、topic 與 artifact 設定 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 本機開發、測試、格式檢查與常見開發注意事項 |
| [RUNBOOK.md](./RUNBOOK.md) | 啟動、健康檢查、任務驗證、故障排查與操作流程 |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | allowlist、prompt injection 檢查、approval 與安全缺口 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | logs、metrics、health checks、audit 與待補監控 |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已實作/部分實作/未實作功能清單 |
| [ROADMAP.md](./ROADMAP.md) | 建議演進路線與里程碑 |

## 快速閱讀順序

1. 先讀 [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)，避免誤把 scaffold 當成完整平台。
2. 再讀 [ARCHITECTURE.md](./ARCHITECTURE.md)，建立系統與資料流視角。
3. 若要啟動專案，讀 [RUNBOOK.md](./RUNBOOK.md) 與 [CONFIGURATION.md](./CONFIGURATION.md)。
4. 若要擴充功能，讀 [DATA_MODEL.md](./DATA_MODEL.md)、[SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) 與 [ROADMAP.md](./ROADMAP.md)。

## 重要現況提醒

- 工作目錄目前不是 git repo。
- API 使用固定 tenant/user UUID，但 schema 有 foreign key；若資料庫沒有 seed 這兩筆資料，建立 task 會失敗。
- `Dockerfile` 會在 build 階段安裝 Playwright Chromium；第一次 build 會下載瀏覽器 runtime，時間較久。
- `metrics.py` 定義了 Prometheus counters/histogram，但目前核心流程沒有更新這些 metrics。
- `docker-compose.yml` 有 MinIO，但目前 artifact store 實作是本地檔案寫入，尚未使用 MinIO client。
- `scripts/create_topics.sh` 預設 `KAFKA_CONTAINER=kafka`；Docker Compose 實際 container 名稱可能不同。
