# 資料模型

資料模型由 `sql/schema.sql` 與 `src/browser_agent/models.py` 定義，Alembic migration `0001_initial.py` 會讀取 `sql/schema.sql` 並逐句執行。

## ERD

```mermaid
erDiagram
    tenants ||--o{ users : has
    tenants ||--o{ tasks : owns
    tenants ||--o{ skills : owns
    users ||--o{ tasks : creates
    users ||--o{ skills : creates
    tasks ||--o{ task_steps : has
    tasks ||--o{ task_artifacts : produces
    task_steps ||--o{ task_artifacts : references
    tasks ||--o{ evaluations : evaluated_by
    tasks ||--o{ approvals : approved_by

    tenants {
      uuid id PK
      text name
      text status
      timestamptz created_at
    }

    users {
      uuid id PK
      uuid tenant_id FK
      text email
      text role
      timestamptz created_at
    }

    tasks {
      uuid id PK
      uuid tenant_id FK
      uuid created_by FK
      text title
      text instructions
      text status
      int priority
      text risk_level
      uuid approved_by FK
      jsonb metadata
    }

    task_steps {
      uuid id PK
      uuid task_id FK
      int step_no
      text action_type
      text target
      text status
      jsonb input_data
      jsonb output_data
    }

    skills {
      uuid id PK
      uuid tenant_id FK
      text name
      text version
      text skill_type
      text entrypoint
      jsonb input_schema
      jsonb output_schema
      text_array policy_tags
    }
```

## 主要資料表

### `tenants`

租戶主檔。目前 API 沒有從 request/auth 判定 tenant，而是使用固定 UUID。

### `users`

使用者主檔。目前 API 沒有登入流程，`created_by` 使用固定 UUID。

### `tasks`

任務主表。

重要欄位：

- `status`：目前實際用到 `created`, `blocked`, `approved`, `executing`, `completed`, `review`。
- `risk_level`：policy 用於阻擋 `high`/`critical`。
- `metadata`：存放 domains、start_url、expected_domain、planner steps、browser_result、evaluation 等。
- `approved_by`：schema/ORM 是 UUID，但 API 目前傳入字串，需修正。

### `task_steps`

由 `TaskRunner` 根據 planner steps 建立。現在只建立 step，尚未在每個 Playwright action 後更新 `status/output_data/error_message`。

### `task_artifacts`

schema 已存在，但目前 `LocalArtifactStore` 只把檔案寫到磁碟，`TaskRunner` 沒有把 artifact rows 寫入此表。artifact URI 目前保存在 `task.metadata.browser_result` 或 evaluation input 中。

### `evaluations`

`TaskRunner` 執行完成後會新增一筆 evaluation。分數來源是：

- final URL 存在：25
- HTML 已擷取：25
- artifacts 有產生：25
- expected domain 命中：25

總分 >= 75 為 `pass`，>= 50 為 `warn`，其餘為 `fail`。

### `approvals`

記錄人工核准資訊。`approved_by` 是 text，和 `tasks.approved_by` 型別不一致。

### `audit_logs`

目前在 task blocked 與 task approved 時寫入。尚未覆蓋 task created、worker execution、policy pass、artifact write、evaluation result 等事件。

## 必要 seed

目前 API 寫入 task 時會引用固定 tenant/user UUID。資料庫初始化後建議先 seed：

```sql
INSERT INTO tenants (id, name, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'active')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, tenant_id, email, role)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',
  'ops@example.com',
  'admin'
)
ON CONFLICT (tenant_id, email) DO NOTHING;
```

## 建議修正

- 將 `tasks.approved_by` 改為 text，或改成真正 user UUID 並新增 `approval_actor_email`。
- 在 migration/seed 腳本內建立 default tenant/user，或移除固定 UUID 假設。
- 將 artifact 寫入 `task_artifacts` 表，避免只存在 metadata。
- 補上狀態 enum/constraint，避免任意 status 字串。
- 補上 idempotency key unique index 與 correlation ID 查詢 index。
