"""Test-only signing keys and token factory that imitate Supabase Auth (ES256 + JWKS)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

ISSUER_BASE = "http://supabase.test"
ISSUER = f"{ISSUER_BASE}/auth/v1"


class TestKeys:
    """An ES256 key pair with a kid, published as a JWKS document."""

    __test__ = False  # not a pytest test class

    def __init__(self, kid: str | None = None) -> None:
        self.kid = kid or str(uuid.uuid4())
        self.private = ec.generate_private_key(ec.SECP256R1())

    def jwk(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(ECAlgorithm.to_jwk(self.private.public_key()))
        data.update({"kid": self.kid, "alg": "ES256", "use": "sig"})
        return data

    def token(
        self,
        sub: uuid.UUID | str,
        *,
        email: str | None = "student@example.com",
        aud: str = "authenticated",
        iss: str | None = ISSUER,
        role: str = "authenticated",
        expires_in: int = 3600,
        extra: dict[str, Any] | None = None,
        kid: str | None = None,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": str(sub),
            "aud": aud,
            "role": role,
            "iat": now,
            "exp": now + expires_in,
        }
        if iss is not None:
            claims["iss"] = iss
        if email is not None:
            claims["email"] = email
        claims.update(extra or {})
        return jwt.encode(claims, self.private, algorithm="ES256", headers={"kid": kid or self.kid})


def jwks_doc(*keys: TestKeys) -> dict[str, Any]:
    return {"keys": [k.jwk() for k in keys]}


class StubFetcher:
    """Async JWKS fetcher returning a mutable document and counting calls."""

    def __init__(self, doc: dict[str, Any]) -> None:
        self.doc = doc
        self.calls = 0
        self.fail = False

    async def __call__(self, url: str) -> dict[str, Any]:
        self.calls += 1
        if self.fail:
            raise ConnectionError("jwks down")
        return self.doc
