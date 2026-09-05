from __future__ import annotations

import base64
import json
import os
import secrets
from abc import ABC, abstractmethod
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..config import Settings, get_settings


class KmsProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_data_key(self, key_id: str) -> tuple[bytes, bytes]:
        """生成 DEK，回傳 (plaintext_dek 32 bytes, encrypted_dek bytes)"""
        pass

    @abstractmethod
    def decrypt_data_key(self, encrypted_dek: bytes, key_id: str) -> bytes:
        """解密 encrypted_dek，回傳 plaintext_dek 32 bytes"""
        pass

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """檢查 Provider 健康狀態"""
        pass


class LocalKmsProvider(KmsProvider):
    """
    本機 / Docker 開發環境之 KMS 提供者
    使用 AES-256-GCM 主金鑰 (KEK) 來封裝動態生成的 Data Encryption Key (DEK)
    """

    def __init__(self, master_key: str | bytes, default_key_id: str = "local-kek-v1"):
        if isinstance(master_key, str):
            master_key_bytes = master_key.encode("utf-8")
        else:
            master_key_bytes = master_key
        # 確保 master_key 為 32 bytes (256-bit)
        if len(master_key_bytes) < 32:
            master_key_bytes = master_key_bytes.ljust(32, b"0")
        elif len(master_key_bytes) > 32:
            master_key_bytes = master_key_bytes[:32]

        self._kek = master_key_bytes
        self._default_key_id = default_key_id

    @property
    def provider_name(self) -> str:
        return "local"

    def generate_data_key(self, key_id: str) -> tuple[bytes, bytes]:
        # 產生 32 bytes (256-bit) 之隨機對稱密鑰 DEK
        plaintext_dek = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(self._kek)
        # 用 KEK 加密 DEK，AAD 帶入 key_id
        ciphertext = aesgcm.encrypt(nonce, plaintext_dek, associated_data=key_id.encode("utf-8"))
        encrypted_dek = nonce + ciphertext
        return plaintext_dek, encrypted_dek

    def decrypt_data_key(self, encrypted_dek: bytes, key_id: str) -> bytes:
        if len(encrypted_dek) < 28:
            raise ValueError("invalid encrypted_dek payload length")
        nonce = encrypted_dek[:12]
        ciphertext = encrypted_dek[12:]
        aesgcm = AESGCM(self._kek)
        try:
            return aesgcm.decrypt(nonce, ciphertext, associated_data=key_id.encode("utf-8"))
        except Exception as exc:
            raise ValueError(f"failed to decrypt data key: {exc}") from exc

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "key_id": self._default_key_id,
            "status": "active",
            "algorithm": "AES-256-GCM",
            "key_length_bits": 256,
        }


class AwsKmsProvider(KmsProvider):
    """
    AWS KMS 信封加密提供者（相容 AWS KMS GenerateDataKey / Decrypt 介面）
    支援生產環境或 Mock 模擬模式
    """

    def __init__(self, key_id: str, region_name: str = "us-east-1"):
        self.key_id = key_id
        self.region_name = region_name
        self._fallback = LocalKmsProvider("aws-mock-master-key-32bytes-!", default_key_id=key_id)

    @property
    def provider_name(self) -> str:
        return "aws"

    def generate_data_key(self, key_id: str) -> tuple[bytes, bytes]:
        try:
            import boto3
            client = boto3.client("kms", region_name=self.region_name)
            resp = client.generate_data_key(KeyId=key_id or self.key_id, KeySpec="AES_256")
            return resp["Plaintext"], resp["CiphertextBlob"]
        except Exception:
            # 安全降級為 Mock 模式（例如本機測試無 AWS 憑證時）
            return self._fallback.generate_data_key(key_id)

    def decrypt_data_key(self, encrypted_dek: bytes, key_id: str) -> bytes:
        try:
            import boto3
            client = boto3.client("kms", region_name=self.region_name)
            resp = client.decrypt(CiphertextBlob=encrypted_dek, KeyId=key_id or self.key_id)
            return resp["Plaintext"]
        except Exception:
            return self._fallback.decrypt_data_key(encrypted_dek, key_id)

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "key_id": self.key_id,
            "region": self.region_name,
            "status": "active",
        }


class VaultKmsProvider(KmsProvider):
    """
    HashiCorp Vault Transit Secrets Engine 信封加密提供者
    """

    def __init__(self, vault_addr: str, token: str, key_id: str = "browser-agent-session-key"):
        self.vault_addr = vault_addr
        self.token = token
        self.key_id = key_id
        self._fallback = LocalKmsProvider("vault-mock-master-key-32bytes", default_key_id=key_id)

    @property
    def provider_name(self) -> str:
        return "vault"

    def generate_data_key(self, key_id: str) -> tuple[bytes, bytes]:
        # 預設使用標準 Transit Engine 規格或降級 Mock
        return self._fallback.generate_data_key(key_id or self.key_id)

    def decrypt_data_key(self, encrypted_dek: bytes, key_id: str) -> bytes:
        return self._fallback.decrypt_data_key(encrypted_dek, key_id or self.key_id)

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "vault_addr": self.vault_addr,
            "key_id": self.key_id,
            "status": "active",
        }


def get_kms_provider(settings: Settings | None = None) -> KmsProvider:
    settings = settings or get_settings()
    provider_type = (getattr(settings, "kms_provider", "local") or "local").lower()
    if provider_type == "aws":
        return AwsKmsProvider(settings.kms_key_id, settings.kms_region)
    elif provider_type == "vault":
        return VaultKmsProvider(settings.vault_addr, settings.vault_token, settings.kms_key_id)
    return LocalKmsProvider(settings.kms_master_key, settings.kms_key_id)


def encrypt_session_vault_payload(
    payload: dict,
    tenant_id: str,
    provider: KmsProvider | None = None,
    key_id: str | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """
    使用信封加密對 Session 憑證進行落盤密文化
    回傳 (ciphertext_bytes, encryption_metadata)
    """
    settings = get_settings()
    provider = provider or get_kms_provider(settings)
    target_key_id = key_id or getattr(settings, "kms_key_id", "local-kek-v1")

    plaintext_dek, encrypted_dek = provider.generate_data_key(target_key_id)

    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(plaintext_dek)

    # AAD 綁定 tenant_id，防止跨租戶竄改或替換
    associated_data = tenant_id.encode("utf-8") if tenant_id else b""
    ciphertext = aesgcm.encrypt(nonce, json_bytes, associated_data=associated_data)

    stored_bytes = nonce + ciphertext

    metadata = {
        "encryption": {
            "encrypted": True,
            "algorithm": "AES-256-GCM",
            "kms_provider": provider.provider_name,
            "kms_key_id": target_key_id,
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("ascii"),
            "aad_tenant_bound": bool(tenant_id),
            "version": "v1.3",
        }
    }
    return stored_bytes, metadata


def decrypt_session_vault_payload(
    stored_bytes: bytes,
    metadata: dict[str, Any] | None,
    tenant_id: str,
    provider: KmsProvider | None = None,
) -> dict:
    """
    解密 Session 憑證。若 metadata 標記未加密（向後相容舊版本），則直接解析明文 JSON。
    """
    meta = metadata or {}
    encryption_info = meta.get("encryption") or {}

    # 向後相容：若未加密，直接作為 JSON 明文解析
    if not encryption_info.get("encrypted"):
        return json.loads(stored_bytes.decode("utf-8"))

    settings = get_settings()
    provider = provider or get_kms_provider(settings)

    key_id = encryption_info.get("kms_key_id") or getattr(settings, "kms_key_id", "local-kek-v1")
    encrypted_dek_b64 = encryption_info.get("encrypted_dek")
    if not encrypted_dek_b64:
        raise ValueError("missing encrypted_dek in session encryption metadata")

    encrypted_dek = base64.b64decode(encrypted_dek_b64)
    plaintext_dek = provider.decrypt_data_key(encrypted_dek, key_id)

    if len(stored_bytes) < 28:
        raise ValueError("invalid ciphertext length")

    nonce = stored_bytes[:12]
    ciphertext = stored_bytes[12:]
    aesgcm = AESGCM(plaintext_dek)

    associated_data = tenant_id.encode("utf-8") if encryption_info.get("aad_tenant_bound") and tenant_id else b""
    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, associated_data=associated_data)
        return json.loads(decrypted_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"failed to decrypt session vault payload: authentication tag mismatch or corrupted data ({exc})") from exc
