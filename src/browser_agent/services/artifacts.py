from __future__ import annotations

from ..storage import LocalArtifactStore

def build_artifact_store(base_path: str) -> LocalArtifactStore:
    return LocalArtifactStore(base_path)
