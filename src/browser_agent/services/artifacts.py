from __future__ import annotations

from ..config import Settings, get_settings
from ..storage import ArtifactStore, LocalArtifactStore, S3ArtifactStore

def build_artifact_store(base_path: str, settings: Settings | None = None) -> ArtifactStore:
    settings = settings or get_settings()
    return build_artifact_store_from_settings(settings, base_path=base_path)


def build_artifact_store_from_settings(settings: Settings, base_path: str | None = None) -> ArtifactStore:
    if settings.artifact_backend.lower() == "s3":
        return S3ArtifactStore(
            endpoint_url=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
        )
    return LocalArtifactStore(base_path or settings.artifact_base_path)
