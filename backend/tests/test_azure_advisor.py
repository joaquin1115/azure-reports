import asyncio

from app.integrations import azure_advisor
from app.models.models import GravedadEnum


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "value": [
                {
                    "id": "rec-1",
                    "properties": {
                        "impact": "High",
                        "category": "Cost",
                        "resourceMetadata": {
                            "resourceId": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/sites/app-1",
                            "resourceName": "app-1",
                        },
                        "shortDescription": {
                            "problem": "Problem text",
                            "solution": "Solution text",
                        },
                        "extendedProperties": {"savingsAmount": "12.50"},
                    },
                }
            ]
        }


class FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, headers):
        return FakeResponse()


def test_obtener_recomendaciones_traduce_campos_sin_anidar_listas(monkeypatch) -> None:
    async def fake_get_access_token(**kwargs):
        return "arm-token"

    async def fake_traducir_textos(textos):
        return [f"ES: {texto}" for texto in textos]

    monkeypatch.setattr(azure_advisor, "_get_access_token", fake_get_access_token)
    monkeypatch.setattr(azure_advisor.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(azure_advisor, "traducir_textos", fake_traducir_textos)

    recomendaciones = asyncio.run(
        azure_advisor.obtener_recomendaciones(
            subscription_id="sub-1",
            gravedad=GravedadEnum.alta,
            tenant_id="tenant-1",
        )
    )

    assert recomendaciones == [
        {
            "id": "rec-1",
            "categoria": "Cost",
            "impacto": "High",
            "recurso": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/sites/app-1",
            "nombre_recurso": "app-1",
            "descripcion": "ES: Problem text",
            "accion": "ES: Solution text",
            "ahorro_mensual_usd": 12.5,
        }
    ]
    assert isinstance(recomendaciones[0]["descripcion"], str)
    assert isinstance(recomendaciones[0]["accion"], str)
