"""Private key derivation, deliberately independent of public experiment seeds."""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SecretFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: int = Field(1, ge=1, le=1)
    master_hex: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)


@dataclass(frozen=True)
class KeyStore:
    master: bytes = field(repr=False)

    @classmethod
    def create(cls) -> "KeyStore":
        return cls(secrets.token_bytes(32))

    @classmethod
    def load(cls, path: Path) -> "KeyStore":
        data = SecretFile.model_validate_json(path.read_text("utf-8"))
        return cls(bytes.fromhex(data.master_hex))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "master_hex": self.master.hex()}, handle)
            handle.write("\n")

    def _number(self, label: str) -> int:
        digest = hmac.new(self.master, f"nullmark-v1/{label}".encode(), hashlib.sha256).digest()
        return int.from_bytes(digest[:4], "big") + 1

    def derive(self, scheme: str, index: int, depth: int = 10) -> dict:
        if scheme == "synthid":
            return {
                "keys": [self._number(f"synthid/{index}/depth/{d}") for d in range(depth)],
                "sampling_table_seed": self._number(f"synthid/{index}/table"),
            }
        if scheme == "kgw":
            return {"hashing_key": self._number(f"kgw/{index}")}
        raise ValueError(f"unknown watermark scheme: {scheme}")


def key_reference(secret: dict) -> str:
    return hashlib.sha256(json.dumps(secret, sort_keys=True).encode()).hexdigest()
