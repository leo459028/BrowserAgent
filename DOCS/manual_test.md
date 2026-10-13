# Operations Center Manual Testing Guide (v1.4.2)

This manual testing guide provides end-to-end operational instructions for verifying the **BrowserAgent Operations Center**.

---

## Environment Initialization

Ensure Docker containers are spun up:

```bash
docker compose up -d --build
```

Execute database schema migrations:
```bash
docker compose exec -T api alembic upgrade head
```

Open your browser and navigate to the Operations Center:
```text
http://127.0.0.1:8000/operations
```
> **Note**: The application provides automatic path redirection: navigating to `http://localhost:8000/operations`, `http://localhost:8000/operation`, or the root path `http://localhost:8000/` will seamlessly route to `/operations`.

---

## Navigation Bar & Health Badges Overview

Upon loading the page, the top navigation bar displays essential platform badges:
- **Title**: Displays `Browser Agent v1.4 Operations Center` with backward compatibility notice (`Browser Agent v1.2 Operations Center compatible`).
- **DLP Shield Badge** (`#dlp-shield-badge`): Real-time Zero-Trust Dynamic DLP status (Green: `DLP Shield: Active`).
- **Cluster Federation Badge** (`#cluster-fed-badge`): Real-time multi-cluster heartbeat status (Green: `Cluster: Federation Online`).
- **SSO Login Button**: Initiates Enterprise OIDC Authorization Code Flow with PKCE.
- **System Alert Badge**: Displays aggregated operational health (Green: `All Systems Normal` or Yellow: `Alerting`).
- **Vault KMS Badge**: Session Vault KMS encryption status (`Vault: KMS (AES-256-GCM)`).
- **Platform Badge**: Kubernetes platform detection (`Platform: K8s/Helm Ready`).
- **OTLP Badge**: OpenTelemetry batch exporter status (`OTLP: Ready`).
- **Identity & RBAC Selector**: Enables switching between `creator`, `approver`, `operator`, and `admin` roles to verify permission isolation.

---

## Step-by-Step UI Verification Guide

### Step 1: Create a Task or Dispatch a Cross-Browser Matrix
1. Scroll to the **`Create Task`** card in the left column.
2. Select `Normal planner task` from the `Scenario` dropdown.
3. **Select Browser Engine**: Use the **`Browser Engine`** dropdown (`#browser-engine-select`) to select `Chromium (Default)`, `Firefox`, or `WebKit`.
4. **Confirm Zero-Trust DLP**: Ensure the checkbox **`Zero-Trust Dynamic DLP Masking & Redaction`** (`#dlp-toggle`) is checked.
5. **Single Task Dispatch**: Click **`Create task`** to dispatch a single task.
6. **Matrix Multi-Engine Dispatch**: Alternatively, click the blue **`Dispatch Matrix (3 Engines)`** button (`#create-matrix-task`) to simultaneously dispatch parallel runs across Chromium, Firefox, and WebKit linked by a shared `matrix_id`.

### Step 2: Observe Pending State & Approval Button Activation
1. Upon creation, the new task appears at the top of the **`Recent Tasks`** list with status **`PENDING_APPROVAL`**.
2. Click the task. The **`Task Detail`** view updates to display task attributes (including Browser Engine and Matrix ID).
3. The **`Approve selected`** button in the top right toggles from disabled grey to active bright green.

### Step 3: Approve Task & Monitor Multi-Priority Queues
1. Click **`Approve selected`** to grant approval.
2. The task status transitions: `queued` ➜ `executing`.
3. In the **`Queues & Worker Pools`** card, verify that:
   - The task is routed to the appropriate Kafka topic (`agent.tasks.high`, `queued`, or `batch`) according to its priority weight.
   - The assigned worker launches the target Playwright browser engine instance.

### Step 4: Bidirectional Remote Takeover (HITL Reverse Control)
1. While the task is in `executing` status, the **`Live Screen Broadcast`** card establishes a WebSocket connection (`WS /v1/tasks/{id}/live-stream`) streaming browser frames at 2 FPS.
2. **Pause Execution (Enter Takeover)**:
   - Click the orange **`Pause (Takeover)`** button (`#btn-pause-takeover`).
   - The status pill (`#takeover-status-pill`) switches to orange **`PAUSED (TAKEOVER)`**. The worker halts its automated steps.
3. **Remote Canvas Click**:
   - Click on an element directly on the canvas stream.
   - The frontend calculates relative coordinates (X, Y) and issues `POST /v1/tasks/{id}/interact` with `action: click`. The worker injects a mouse click into the live browser page.
4. **Remote Key Input**:
   - In the **`Remote Key Input`** box (`#remote-key-input`), type text (e.g., `PASS_CAPTCHA_123`).
   - Click **`Send Keys`** (`#btn-send-keys`) to inject keystrokes (`action: type`).
5. **Resume Automation**:
   - Click the green **`Resume Task`** button (`#btn-resume-takeover`).
   - The worker resumes execution, recording intervention duration in audit logs with `task.human_intervened = True`.

### Step 5: Verify Cross-Browser Matrix Comparison Panel
1. Locate the **`Cross-Browser Matrix Comparison`** panel (`#matrix-comparison-section`) at the bottom.
2. Enter the `Matrix ID` and click **`Compare Matrix`**.
3. View the side-by-side comparison across Chromium, Firefox, and WebKit:
   - Execution status (`completed` / `failed`)
   - Duration in milliseconds
   - Verdict score (`pass` / `fail`)
   - Self-healing flags (`self_healed`)
   - DLP masking flags (`dlp_masked`)
   - Human intervention flags (`human_intervened`)

### Step 6: Verify Zero-Trust DLP Masking & Redaction
1. Inspect the **`Zero-Trust Dynamic DLP Status`** panel (`#dlp-section`).
2. Verify that active rules include `password_kv`, `bearer_token`, `jwt_pattern`, `openai_api_key`, and `aws_access_key`.
3. In the live stream or downloaded screenshots, confirm that:
   - All password fields (`input[type="password"]`) are rendered with Gaussian blur (`filter: blur(8px)`).
   - Sensitive tokens in logs and metadata are replaced with `[REDACTED_TOKEN]`.

### Step 7: Verify Multi-Cluster Federation & Failover
1. Inspect the **`Multi-Cluster Scheduling Federation Topology`** panel (`#federation-section`).
2. Verify node status, geographic regions, heartbeat age, and the current Leader indicator.
3. **Failover Re-election Drill**: Click **`Force Re-election`** next to a standby node (`POST /v1/ops/federation/re-election`) to verify immediate leadership migration without service interruption.

### Step 8: Verify Full Video Recording Playback
1. For tasks recorded with `record_video=True`, the **`Full WebM Video Recording`** card displays an embedded HTML5 player.
2. Play, pause, or scrub the video to review the complete browser interaction.

### Step 9: Verify Session Vault KMS Encryption & Validation
1. Inspect the **`Session Vault`** card.
2. Click **`Refresh`** to load stored credentials.
3. Click **`Validate`** next to a session to execute a live KMS decryption round-trip and verify AAD tenant integrity.
4. Click **`Revoke`** to mark a session revoked.

### Step 10: Verify Scheduled Tasks Cron Dispatching
1. Inspect the **`Scheduled Tasks`** card.
2. Create a schedule with a standard Cron expression (e.g., `0 9 * * *`).
3. Click **`Run Now`** to immediately dispatch an execution instance.

### Step 11: Verify Distributed Tracing & Alerting
1. Copy the **`Trace ID`** of a completed task, paste it into the **`Trace Inspector`**, and click **`Lookup`** to view the hierarchical span tree.
2. In the **`Production Alerting Center`**, click **`Test Dispatch`** to trigger an asynchronous test webhook notification.

---

## Frequently Asked Questions (FAQ)

### Q1: Why is the `Approve selected` button greyed out and unclickable?
**Answer: This is a built-in safety guardrail.**
- `Approve selected` is only active when a task in **`PENDING_APPROVAL`** state is selected.
- If no task is selected, or if the selected task is already **`COMPLETED`**, `FAILED`, or `QUEUED`, the button remains disabled to prevent duplicate approvals.

### Q2: When are the HITL Takeover controls (`Pause`, `Resume`, `Send Keys`) enabled?
**Answer:**
- `Pause (Takeover)` is enabled only when the selected task is in `executing` status.
- Once paused, the status changes to **`PAUSED (TAKEOVER)`**, enabling canvas clicking, the text input field, `Send Keys`, and `Resume Task`.
- Resuming or finishing the task automatically locks the controls again.

### Q3: What is the difference between single task creation and `Dispatch Matrix`?
**Answer:**
- Single task creation launches one task targeting the selected browser engine.
- `Dispatch Matrix (3 Engines)` automatically generates three separate tasks (Chromium, Firefox, WebKit) sharing the same `matrix_id`, enabling cross-engine rendering and performance comparison.

### Q4: Does Zero-Trust DLP blur affect automation scripts?
**Answer: No.**
- DLP applies CSS visual blur masks (`filter: blur(8px)`) and sanitizes outgoing artifacts. The underlying DOM tree and locator queries remain fully intact for Playwright automation.

### Q5: What happens if the federation leader node fails?
**Answer: Standby nodes trigger automated failover.**
- The Leader node must renew its distributed lease every 5 seconds (TTL: 30s). If heartbeats cease, standby nodes automatically elect a new Leader during the next cycle, ensuring uninterrupted schedule dispatching.

---

## Minimum Acceptance Checklist

- [ ] Top navigation bar renders `Browser Agent v1.4 Operations Center` with active badges (`DLP Shield: Active`, `Cluster: Federation Online`, `Alert Badge`, `K8s Badge`, `OTLP Badge`, `Vault KMS Badge`).
- [ ] Task creation supports engine selection (Chromium, Firefox, WebKit) and one-click matrix dispatch.
- [ ] Live telemetry stream broadcasts browser frames via WebSockets at 2 FPS.
- [ ] HITL takeover allows pausing, remote canvas clicking, key typing, and resumption.
- [ ] Cross-browser matrix panel compares durations, verdicts, and self-healing across engines.
- [ ] Zero-Trust DLP blurs password fields and scrubs secret tokens from metadata.
- [ ] Multi-cluster federation panel shows node heartbeats and supports forced re-election.
- [ ] Priority queues card reflects traffic across High, Queued, and Batch topics.
- [ ] Session Vault allows KMS validation and one-click revocation.
- [ ] Scheduled tasks engine supports Cron scheduling and `Run Now` execution.
- [ ] WebM video player renders recorded browser sessions.
- [ ] Alerting center evaluates 7 operational rules and supports test dispatches.
- [ ] Trace inspector renders hierarchical span trees from Trace IDs.
- [ ] RBAC enforcement restricts unauthorized actions across roles (`creator`, `approver`, `operator`, `admin`).
- [ ] Dead Letter Queue supports individual replay, bulk replay, and quarantine.

---

## PowerShell Automated Smoke Verification Script

Execute the following PowerShell script to verify all core v1.4.2 endpoints:

```powershell
# 1. Acquire tokens across all roles
$operator = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"operator"}'
$creator = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"creator"}'
$approver = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"approver"}'
$admin = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"admin"}'

$opHeaders = @{ Authorization = "Bearer $($operator.access_token)" }
$creatorHeaders = @{ Authorization = "Bearer $($creator.access_token)" }
$approverHeaders = @{ Authorization = "Bearer $($approver.access_token)" }
$adminHeaders = @{ Authorization = "Bearer $($admin.access_token)" }

# 2. Check DLP status and cluster federation topology
$dlpStatus = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/dlp/status -Headers $opHeaders
Write-Host "DLP Status: $($dlpStatus.status), Active Rules: $($dlpStatus.active_rules.Count)" -ForegroundColor Cyan

$fedNodes = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/federation/nodes -Headers $opHeaders
Write-Host "Cluster Status: $($fedNodes.cluster_status), Leader Node: $($fedNodes.leader_node_id)" -ForegroundColor Cyan

# 3. Create a Firefox browser task
$ffTaskBody = @{
    title = "Firefox Rendering Verification"
    instructions = "Navigate to allowlisted site and verify layout"
    browser_engine = "firefox"
    priority = 1
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
    }
} | ConvertTo-Json
$ffTask = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $creatorHeaders -ContentType "application/json" -Body $ffTaskBody
Write-Host "Created Task ID: $($ffTask.task_id), Engine: $($ffTask.browser_engine)" -ForegroundColor Green

# 4. Verify HITL Takeover APIs (Pause / Interact / Resume)
$pauseRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/pause" -Headers $opHeaders -ContentType "application/json" -Body '{"reason":"Manual Inspection"}'
Write-Host "Task Paused for HITL: $($pauseRes.paused)" -ForegroundColor Yellow

$interactRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/interact" -Headers $opHeaders -ContentType "application/json" -Body '{"action":"click","x":150.0,"y":200.0}'
Write-Host "Action Queued: $($interactRes.queued)" -ForegroundColor Yellow

$resumeRes = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($ffTask.task_id)/resume" -Headers $opHeaders
Write-Host "Task Resumed: $($resumeRes.resumed)" -ForegroundColor Green

# 5. Dispatch cross-browser matrix task (Chromium, Firefox, WebKit)
$matrixBody = @{
    title = "E2E Cross-Browser Matrix Suite"
    instructions = "Verify form layout and submission across all 3 engines"
    engines = @("chromium", "firefox", "webkit")
    priority = 1
    risk_level = "low"
    metadata = @{
        domains = @("example.com")
        start_url = "https://example.com"
    }
} | ConvertTo-Json
$matrixRes = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks/matrix -Headers $creatorHeaders -ContentType "application/json" -Body $matrixBody
Write-Host "Matrix Dispatched! Matrix ID: $($matrixRes.matrix_id), Total Tasks: $($matrixRes.total_tasks)" -ForegroundColor Cyan

# 6. Retrieve matrix summary
$matrixSummary = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/tasks/matrix/$($matrixRes.matrix_id)" -Headers $opHeaders
Write-Host "Matrix Tasks Count: $($matrixSummary.tasks.Count)" -ForegroundColor Green
Write-Host "v1.4.2 Verification Completed Successfully!" -ForegroundColor Green
```
