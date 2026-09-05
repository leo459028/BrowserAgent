from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionAbortedException(Exception):
    """當維運人員發起線上 Abort 時拋出之中斷異常"""
    def __init__(self, task_id: str, reason: str = "Execution aborted by operator"):
        self.task_id = task_id
        self.reason = reason
        super().__init__(f"Task {task_id} aborted: {reason}")


class LiveTelemetryBroadcaster:
    """
    管理 Playwright 執行中畫面的 WebSocket 即時廣播與線上中斷 (Abort) 狀態
    支援多個 Operations Center 前端客戶端同時訂閱同一個執行中任務的畫面串流
    """

    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._latest_frames: dict[str, dict[str, Any]] = {}
        self._aborted_tasks: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def publish_frame(
        self,
        task_id: str,
        frame_bytes: bytes,
        step_no: int | None = None,
        action: str | None = None,
        url: str | None = None,
    ) -> None:
        """發布單一畫面幀至廣播通道（線程安全，由 Worker 呼叫）"""
        frame_b64 = base64.b64encode(frame_bytes).decode("ascii")
        payload = {
            "type": "frame",
            "task_id": task_id,
            "timestamp": time.time(),
            "step_no": step_no,
            "action": action,
            "url": url,
            "data": f"data:image/jpeg;base64,{frame_b64}",
        }
        self._latest_frames[task_id] = payload

        # 若當前事件循環正在運行，向所有訂閱者推播
        subscribers = self._subscribers.get(task_id, set())
        for queue in list(subscribers):
            try:
                queue.put_nowait(payload)
            except Exception:
                pass

    def get_latest_frame(self, task_id: str) -> dict[str, Any] | None:
        return self._latest_frames.get(task_id)

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """客戶端連線 WebSocket 時註冊為訂閱者"""
        async with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            queue: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._subscribers[task_id].add(queue)

            # 若已有最新幀，立即補發第一幀給新連線客戶端
            if task_id in self._latest_frames:
                queue.put_nowait(self._latest_frames[task_id])
            return queue

    async def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(task_id)
            if subscribers and queue in subscribers:
                subscribers.remove(queue)
            if subscribers is not None and len(subscribers) == 0:
                self._subscribers.pop(task_id, None)

    def request_abort(self, task_id: str, reason: str = "Operator manually requested abort") -> None:
        """標記任務為中止請求狀態"""
        self._aborted_tasks[task_id] = {
            "aborted": True,
            "reason": reason,
            "timestamp": time.time(),
        }
        logger.warning("Abort requested for task %s: %s", task_id, reason)

        # 通知 WebSocket 訂閱端已中止
        abort_payload = {
            "type": "aborted",
            "task_id": task_id,
            "reason": reason,
            "timestamp": time.time(),
        }
        for queue in list(self._subscribers.get(task_id, set())):
            try:
                queue.put_nowait(abort_payload)
            except Exception:
                pass

    def is_aborted(self, task_id: str) -> bool:
        return task_id in self._aborted_tasks

    def get_abort_info(self, task_id: str) -> dict[str, Any] | None:
        return self._aborted_tasks.get(task_id)

    def clear_task(self, task_id: str) -> None:
        self._latest_frames.pop(task_id, None)
        self._aborted_tasks.pop(task_id, None)
        self._subscribers.pop(task_id, None)


_broadcaster_instance: LiveTelemetryBroadcaster | None = None

def get_telemetry_broadcaster() -> LiveTelemetryBroadcaster:
    global _broadcaster_instance
    if _broadcaster_instance is None:
        _broadcaster_instance = LiveTelemetryBroadcaster()
    return _broadcaster_instance
