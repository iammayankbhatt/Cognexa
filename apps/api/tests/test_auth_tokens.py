"""Unit tests for JWT verification and the JWKS cache (no network, no database)."""

from __future__ import annotations

import time
import uuid

import jwt
import pytest

from app.auth.jwks import JwksCache
from app.auth.tokens import AuthUnavailableError, TokenError, verify_token
from app.core.config import Settings
from tests.auth_helpers import ISSUER, ISSUER_BASE, StubFetcher, TestKeys, jwks_doc


def settings(**kw: object) -> Settings:
    base: dict[str, object] = {"_env_file": None, "supabase_url": ISSUER_BASE}
    base.update(kw)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
def keys() -> TestKeys:
    return TestKeys()


@pytest.fixture
def cache(keys: TestKeys) -> JwksCache:
    return JwksCache("http://jwks.test", fetcher=StubFetcher(jwks_doc(keys)))


async def test_valid_token_is_accepted(keys: TestKeys, cache: JwksCache) -> None:
    uid = uuid.uuid4()
    claims = await verify_token(keys.token(uid, email="a@b.c"), settings(), cache)
    assert claims.user_id == uid and claims.email == "a@b.c"


@pytest.mark.parametrize(
    ("kwargs", "label"),
    [
        ({"expires_in": -120}, "expired"),
        ({"aud": "anon"}, "wrong audience"),
        ({"iss": "http://evil.test/auth/v1"}, "wrong issuer"),
        ({"role": "service_role"}, "service role token"),
        ({"sub": "not-a-uuid"}, "subject not a uuid"),
    ],
)
async def test_bad_claims_are_rejected(
    keys: TestKeys, cache: JwksCache, kwargs: dict[str, object], label: str
) -> None:
    sub = kwargs.pop("sub", uuid.uuid4())
    token = keys.token(sub, **kwargs)  # type: ignore[arg-type]
    with pytest.raises(TokenError):
        await verify_token(token, settings(), cache)


async def test_token_signed_by_another_key_is_rejected(cache: JwksCache) -> None:
    impostor = TestKeys()  # different key, unknown kid
    with pytest.raises(TokenError):
        await verify_token(impostor.token(uuid.uuid4()), settings(), cache)


async def test_forged_kid_with_wrong_key_is_rejected(keys: TestKeys, cache: JwksCache) -> None:
    impostor = TestKeys()
    token = impostor.token(uuid.uuid4(), kid=keys.kid)  # claims our kid, signed with another key
    with pytest.raises(TokenError):
        await verify_token(token, settings(), cache)


async def test_malformed_and_alg_none_tokens_are_rejected(cache: JwksCache) -> None:
    with pytest.raises(TokenError):
        await verify_token("not.a.jwt", settings(), cache)
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        key=None,
        algorithm="none",
    )
    with pytest.raises(TokenError):
        await verify_token(unsigned, settings(), cache)


async def test_hs256_only_with_configured_secret() -> None:
    uid = uuid.uuid4()
    secret = "test-secret-with-enough-length-0123456789"
    token = jwt.encode(
        {"sub": str(uid), "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 60},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        await verify_token(token, settings(), None)
    with pytest.raises(TokenError):  # placeholder value counts as unset
        await verify_token(token, settings(supabase_jwt_secret="REPLACE_ME"), None)
    claims = await verify_token(token, settings(supabase_jwt_secret=secret), None)
    assert claims.user_id == uid


async def test_asymmetric_token_without_jwks_is_unavailable(keys: TestKeys) -> None:
    with pytest.raises(AuthUnavailableError):
        await verify_token(keys.token(uuid.uuid4()), settings(), None)


async def test_jwks_is_cached_and_refetched_for_rotated_key() -> None:
    old = TestKeys()
    stub = StubFetcher(jwks_doc(old))
    now = [1000.0]
    cache = JwksCache(
        "http://jwks.test", ttl_s=600, min_refetch_s=30, fetcher=stub, clock=lambda: now[0]
    )
    await verify_token(old.token(uuid.uuid4()), settings(), cache)
    await verify_token(old.token(uuid.uuid4()), settings(), cache)
    assert stub.calls == 1  # cached

    new = TestKeys()
    stub.doc = jwks_doc(old, new)
    with pytest.raises(TokenError):  # too soon to refetch: unknown kid
        await verify_token(new.token(uuid.uuid4()), settings(), cache)
    now[0] += 31
    await verify_token(new.token(uuid.uuid4()), settings(), cache)  # refetched after rotation
    assert stub.calls == 2

    now[0] += 601
    await verify_token(new.token(uuid.uuid4()), settings(), cache)  # TTL expired
    assert stub.calls == 3


async def test_jwks_outage_is_reported_as_unavailable(keys: TestKeys) -> None:
    stub = StubFetcher(jwks_doc(keys))
    stub.fail = True
    cache = JwksCache("http://jwks.test", fetcher=stub)
    with pytest.raises(AuthUnavailableError):
        await verify_token(keys.token(uuid.uuid4()), settings(), cache)


def test_placeholder_settings_count_as_unset() -> None:
    s = Settings(
        _env_file=None,
        supabase_url="REPLACE_ME",
        supabase_jwks_url=" ",
        database_url="REPLACE_ME",
    )
    assert s.supabase_url is None and s.effective_jwks_url is None and s.database_url is None
    s2 = Settings(_env_file=None, supabase_url="http://x.test/")
    assert s2.jwt_issuer == "http://x.test/auth/v1"
    assert s2.effective_jwks_url == "http://x.test/auth/v1/.well-known/jwks.json"
