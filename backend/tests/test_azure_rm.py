import asyncio

from app.integrations import azure_rm


def test_get_access_token_usa_tenant_client_secret(monkeypatch) -> None:
    captured = {}

    class FakeCredential:
        def __init__(self, *, tenant_id: str, client_id: str, client_secret: str) -> None:
            captured["tenant_id"] = tenant_id
            captured["client_id"] = client_id
            captured["client_secret"] = client_secret
            self.closed = False

        async def get_token(self, scope: str):
            captured["scope"] = scope

            class Token:
                token = "arm-token"

            return Token()

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(azure_rm, "ClientSecretCredential", FakeCredential)

    token = asyncio.run(azure_rm._get_access_token(
        tenant_id="tenant-test",
        client_id="client-test",
        client_secret="secret-test",
    ))

    assert token == "arm-token"
    assert captured == {
        "tenant_id": "tenant-test",
        "client_id": "client-test",
        "client_secret": "secret-test",
        "scope": "https://management.azure.com/.default",
        "closed": True,
    }


def test_validar_tenant_solo_valida_token_sin_consultar_audience(monkeypatch) -> None:
    calls = []

    async def fake_get_access_token(*, tenant_id, client_id=None, client_secret=None):
        calls.append({"tenant_id": tenant_id, "client_id": client_id, "client_secret": client_secret})
        return "arm-token"

    monkeypatch.setattr(azure_rm, "_get_access_token", fake_get_access_token)

    assert asyncio.run(azure_rm.validar_tenant("tenant-test")) is True
    assert calls == [{"tenant_id": "tenant-test", "client_id": None, "client_secret": None}]
