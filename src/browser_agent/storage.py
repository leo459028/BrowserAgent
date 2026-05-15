from __future__ import annotations

import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class StoredArtifact:
    uri: str
    sha256: str

class LocalArtifactStore:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, task_id: str, artifact_type: str, data: bytes, suffix: str = "") -> StoredArtifact:
        day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        folder = self.base_path / day / task_id
        folder.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(data).hexdigest()
        filename = f"{artifact_type}-{sha[:12]}{suffix}"
        path = folder / filename
        path.write_bytes(data)
        return StoredArtifact(uri=str(path), sha256=sha)
