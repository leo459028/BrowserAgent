from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from .. import models

logger = logging.getLogger(__name__)


class ClusterFederationManager:
    """
    多叢集排程同盟與高可用容災接管 (Multi-Cluster Federation & HA Failover)
    負責維護跨叢集節點心跳、Leader 租約選舉與排程容災漂移
    """

    def __init__(
        self,
        node_id: str = "node-local-1",
        region: str = "local-dev",
        lease_ttl_seconds: int = 30,
    ):
        self.node_id = node_id
        self.region = region
        self.lease_ttl_seconds = lease_ttl_seconds

        # 本機節點記憶體狀態（加速查詢與測試）
        self._memory_nodes: dict[str, dict[str, Any]] = {
            self.node_id: {
                "node_id": self.node_id,
                "region": self.region,
                "is_leader": True,
                "status": "healthy",
                "last_heartbeat": time.time(),
                "active_schedules_count": 0,
                "metadata": {"version": "1.4.0", "role": "primary"},
            }
        }

    def register_heartbeat(
        self,
        node_id: str,
        region: str,
        active_schedules_count: int = 0,
        metadata: dict[str, Any] | None = None,
        is_leader: bool | None = None,
        db_session: Session | None = None,
    ) -> dict[str, Any]:
        """
        註冊或更新節點心跳
        """
        now = time.time()
        existing = self._memory_nodes.get(node_id)
        current_leader = existing["is_leader"] if existing else False
        if is_leader is not None:
            current_leader = is_leader

        node_data = {
            "node_id": node_id,
            "region": region,
            "is_leader": current_leader,
            "status": "healthy",
            "last_heartbeat": now,
            "active_schedules_count": active_schedules_count,
            "metadata": metadata or {},
        }
        self._memory_nodes[node_id] = node_data

        # 若提供了 DB Session，同步持久化至 cluster_nodes 資料表
        if db_session:
            try:
                db_node = db_session.get(models.ClusterNode, node_id)
                if not db_node:
                    db_node = models.ClusterNode(
                        id=node_id,
                        region=region,
                        is_leader=current_leader,
                        status="healthy",
                        last_heartbeat_at=datetime.fromtimestamp(now, timezone.utc),
                        active_schedules_count=active_schedules_count,
                        metadata_=metadata or {},
                    )
                    db_session.add(db_node)
                else:
                    db_node.region = region
                    db_node.is_leader = current_leader
                    db_node.status = "healthy"
                    db_node.last_heartbeat_at = datetime.fromtimestamp(now, timezone.utc)
                    db_node.active_schedules_count = active_schedules_count
                    db_node.metadata_ = metadata or {}
                    db_node.updated_at = datetime.fromtimestamp(now, timezone.utc)
                db_session.commit()
            except Exception as e:
                logger.warning("Failed to persist cluster node to DB: %s", e)
                db_session.rollback()

        return node_data

    def evaluate_leadership(self) -> str:
        """
        評估同盟叢集 Leader 租約有效性
        若現任 Leader 失聯超逾 lease_ttl，自動觸發容災選舉，回傳當前/新選出之 Leader node_id
        """
        now = time.time()
        current_leader_id: str | None = None

        # 檢視現有節點狀態
        for nid, data in self._memory_nodes.items():
            age = now - data["last_heartbeat"]
            if age > self.lease_ttl_seconds:
                data["status"] = "offline"
                if data["is_leader"]:
                    logger.warning("Cluster leader %s heartbeat timed out (age=%.1fs), stepping down", nid, age)
                    data["is_leader"] = False
            else:
                data["status"] = "healthy"
                if data["is_leader"]:
                    current_leader_id = nid

        # 若無有效 Leader，從健康的節點中自動選舉一位（優先選擇本地節點，次依 node_id 排序）
        if not current_leader_id:
            healthy_candidates = [
                nid for nid, data in self._memory_nodes.items() if data["status"] == "healthy"
            ]
            if healthy_candidates:
                # 排序穩定選舉
                new_leader = self.node_id if self.node_id in healthy_candidates else sorted(healthy_candidates)[0]
                self._memory_nodes[new_leader]["is_leader"] = True
                current_leader_id = new_leader
                logger.info("Cluster failover: elected new leader node %s", new_leader)
            else:
                # 無健康節點，本地節點自我修復
                self._memory_nodes[self.node_id]["status"] = "healthy"
                self._memory_nodes[self.node_id]["is_leader"] = True
                self._memory_nodes[self.node_id]["last_heartbeat"] = now
                current_leader_id = self.node_id

        return current_leader_id

    def force_reelection(self, target_node_id: str | None = None) -> str:
        """
        手動或因應運維指令強制轉移/重新選舉 Leader
        """
        target = target_node_id or self.node_id
        if target not in self._memory_nodes:
            self.register_heartbeat(target, "default", is_leader=False)

        for nid, data in self._memory_nodes.items():
            data["is_leader"] = (nid == target)
        logger.info("Leadership forcibly transferred to node %s", target)
        return target

    def get_topology(self) -> dict[str, Any]:
        """
        取得整體同盟叢集拓撲資訊
        """
        self.evaluate_leadership()
        nodes_list = []
        leader_id = None
        healthy_count = 0

        for nid, data in self._memory_nodes.items():
            if data["is_leader"]:
                leader_id = nid
            if data["status"] == "healthy":
                healthy_count += 1
            nodes_list.append({
                "node_id": nid,
                "region": data["region"],
                "is_leader": data["is_leader"],
                "status": data["status"],
                "last_heartbeat_ago_seconds": round(time.time() - data["last_heartbeat"], 1),
                "active_schedules_count": data["active_schedules_count"],
                "metadata": data.get("metadata", {}),
            })

        return {
            "cluster_status": "healthy" if leader_id else "degraded",
            "leader_node_id": leader_id,
            "total_nodes": len(nodes_list),
            "healthy_nodes": healthy_count,
            "local_node_id": self.node_id,
            "local_region": self.region,
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "nodes": nodes_list,
        }


_federation_manager_instance: ClusterFederationManager | None = None


def get_federation_manager() -> ClusterFederationManager:
    global _federation_manager_instance
    if _federation_manager_instance is None:
        from ..config import get_settings
        settings = get_settings()
        _federation_manager_instance = ClusterFederationManager(
            node_id=settings.federation_node_id,
            region=settings.federation_region,
            lease_ttl_seconds=settings.federation_lease_ttl_seconds,
        )
    return _federation_manager_instance
