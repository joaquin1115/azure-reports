import asyncio
from types import SimpleNamespace

from app.auth import dependencies


def test_get_current_user_no_valida_audience(monkeypatch) -> None:
    captured = {}

    async def fake_get_jwks() -> dict:
        return {"keys": [{"kid": "kid-test", "kty": "RSA"}]}

    def fake_get_unverified_header(token: str) -> dict:
        captured["header_token"] = token
        return {"kid": "kid-test"}

    def fake_decode(token: str, key: dict, algorithms: list[str], options: dict) -> dict:
        captured["decode"] = {
            "token": token,
            "key": key,
            "algorithms": algorithms,
            "options": options,
        }
        return {"email": "usuario@example.com"}

    monkeypatch.setattr(dependencies, "_get_jwks", fake_get_jwks)
    monkeypatch.setattr(dependencies.jwt, "get_unverified_header", fake_get_unverified_header)
    monkeypatch.setattr(dependencies.jwt, "decode", fake_decode)

    payload = asyncio.run(dependencies.get_current_user(
        credentials=SimpleNamespace(credentials="jwt-test"),
        token=None,
    ))

    assert payload == {"email": "usuario@example.com"}
    assert captured["header_token"] == "jwt-test"
    assert captured["decode"] == {
        "token": "jwt-test",
        "key": {"kid": "kid-test", "kty": "RSA"},
        "algorithms": ["RS256"],
        "options": {"verify_aud": False},
    }
