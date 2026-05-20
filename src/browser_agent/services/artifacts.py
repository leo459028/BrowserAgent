from __future__ import annotations

from ..storage import ArtifactStore, LocalArtifactStore

def build_artifact_store(base_path: str) -> ArtifactStore:
    return LocalArtifactStore(base_path)
