from __future__ import annotations

import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
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

    def read_bytes(self, uri: str) -> bytes:
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

    def read_bytes(self, uri: str) -> bytes:
        path = Path(uri)
        if not path.is_absolute():
            path = self.base_path / path
        return path.read_bytes()


class S3ArtifactStore:
    backend = "s3"

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        redactor: ArtifactRedactor | None = None,
        client=None,
    ):
        self.endpoint_url = endpoint_url
        self.bucket = bucket
        self.redactor = redactor or NoopArtifactRedactor()
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                endpoint_url=f"http://{endpoint_url}" if "://" not in endpoint_url else endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(s3={"addressing_style": "path"}),
            )
        self.client = client
        self.ensure_bucket()

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

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
        sha = hashlib.sha256(redacted_data).hexdigest()
        key = f"{day}/{task_id}/{artifact_type}-{sha[:12]}{suffix}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=redacted_data,
            ContentType=content_type,
        )
        return StoredArtifact(
            uri=f"s3://{self.bucket}/{key}",
            sha256=sha,
            content_type=content_type,
            size_bytes=len(redacted_data),
            backend=self.backend,
            metadata={
                "backend": self.backend,
                "bucket": self.bucket,
                "key": key,
                "content_type": content_type,
                "size_bytes": len(redacted_data),
                "retention": {
                    "policy": "default",
                    "expires_at": None,
                },
                "redaction": redaction_metadata,
            },
        )

    def read_bytes(self, uri: str) -> bytes:
        parsed = urlparse(uri)
        bucket = parsed.netloc or self.bucket
        key = parsed.path.lstrip("/")
        obj = self.client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
