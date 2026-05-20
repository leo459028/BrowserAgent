from __future__ import annotations

import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

@dataclass
class StoredArtifact:
    uri: str
    sha256: str
    content_type: str
    size_bytes: int
    backend: str
    metadata: dict


class ArtifactRedactor(Protocol):
    def redact(self, artifact_type: str, data: bytes, content_type: str) -> tuple[bytes, dict]:
        ...


class NoopArtifactRedactor:
    def redact(self, artifact_type: str, data: bytes, content_type: str) -> tuple[bytes, dict]:
        return data, {
            "status": "not_applied",
            "strategy": "noop",
        }


class ArtifactStore(Protocol):
    backend: str

    def write_bytes(
        self,
        task_id: str,
        artifact_type: str,
        data: bytes,
        suffix: str = "",
        content_type: str = "application/octet-stream",
    ) -> StoredArtifact:
        ...

class LocalArtifactStore:
    backend = "local"

    def __init__(self, base_path: str | Path, redactor: ArtifactRedactor | None = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.redactor = redactor or NoopArtifactRedactor()

    def write_bytes(
        self,
        task_id: str,
        artifact_type: str,
        data: bytes,
        suffix: str = "",
        content_type: str = "application/octet-stream",
    ) -> StoredArtifact:
        redacted_data, redaction_metadata = self.redactor.redact(artifact_type, data, content_type)
        day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        folder = self.base_path / day / task_id
        folder.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(redacted_data).hexdigest()
        filename = f"{artifact_type}-{sha[:12]}{suffix}"
        path = folder / filename
        path.write_bytes(redacted_data)
        return StoredArtifact(
            uri=str(path),
            sha256=sha,
            content_type=content_type,
            size_bytes=len(redacted_data),
            backend=self.backend,
            metadata={
                "backend": self.backend,
                "content_type": content_type,
                "size_bytes": len(redacted_data),
                "retention": {
                    "policy": "default",
                    "expires_at": None,
                },
                "redaction": redaction_metadata,
            },
        )


class S3ArtifactStore:
    backend = "s3"

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("S3 artifact backend is reserved for a later v0.3 deployment slice")
