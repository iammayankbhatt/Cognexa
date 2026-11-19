"""Verify a Supabase access token and extract the identity claims.

Checked against a real local Supabase token (2026-11-19, Supabase CLI 3.2.0): header
`{"alg": "ES256", "kid": ...}`, claims `iss = <SUPABASE_URL>/auth/v1`, `aud = "authenticated"`,
`sub` = user id (uuid), `email`, `role = "authenticated"`, `exp`, `iat`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from jwt.exceptions import InvalidTokenError

from app.auth.jwks import JwksCache, JwksUnavailableError
from app.core.config import Settings

ASYMMETRIC = {"ES256", "RS256", "EdDSA"}


class TokenError(Exception):
    """The token is missing, malformed, expired or not signed by our project."""


class AuthUnavailableError(Exception):
    """Verification is impossible right now (JWKS unreachable or auth not configured)."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    email: str | None
    token_role: str  # the Postgres role claim, normally "authenticated"


async def verify_token(token: str, settings: Settings, jwks: JwksCache | None) -> TokenClaims:
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise TokenError("malformed token") from exc
    alg = header.get("alg")

    key: object
    if alg in ASYMMETRIC:
        kid = header.get("kid")
        if jwks is None:
            raise AuthUnavailableError("JWKS URL is not configured")
        if not kid:
            raise TokenError("token has no key id")
        try:
            jwk = await jwks.get_key(kid)
        except JwksUnavailableError as exc:
            raise AuthUnavailableError(str(exc)) from exc
        if jwk is None:
            raise TokenError("unknown signing key")
        key = jwk.key
    elif alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise TokenError("HS256 tokens are not accepted (no legacy secret configured)")
        key = settings.supabase_jwt_secret
    else:
        raise TokenError("unsupported signing algorithm")

    options = {"require": ["exp", "sub", "aud"]}
    try:
        claims = jwt.decode(
            token,
            key=key,  # type: ignore[arg-type]
            algorithms=[alg],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,  # None skips the check (tests without SUPABASE_URL)
            options=options,  # type: ignore[arg-type]
            leeway=10,
        )
    except InvalidTokenError as exc:
        raise TokenError(f"invalid token: {type(exc).__name__}") from exc

    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except ValueError as exc:
        raise TokenError("subject is not a user id") from exc
    if claims.get("role") not in (None, "authenticated"):
        raise TokenError("token is not a signed-in user token")
    email = claims.get("email")
    return TokenClaims(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        token_role=str(claims.get("role", "authenticated")),
    )
