import httpx
from app.models.models import GravedadEnum
from app.integrations.azure_rm import _get_access_token

GRAVEDAD_MAP = {
    GravedadEnum.alta: ["High"],
    GravedadEnum.media: ["Medium"],
    GravedadEnum.ambas: ["High", "Medium"],
}


async def obtener_recomendaciones(
    subscription_id: str,
    tenant_id: str,
    gravedad: GravedadEnum,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict]:
    token = await _get_access_token(tenant_id, client_id, client_secret)
    niveles = GRAVEDAD_MAP[gravedad]
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/providers/Microsoft.Advisor/recommendations?api-version=2023-01-01"
    )
    recomendaciones = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("value", []):
            props = item.get("properties", {})
            nivel = props.get("impact", "")
            if nivel in niveles:
                recomendaciones.append({
                    "id": item.get("id"),
                    "categoria": props.get("category", ""),
                    "impacto": nivel,
                    "recurso": props.get("resourceMetadata", {}).get("resourceId", ""),
                    "nombre_recurso": props.get("shortDescription", {}).get("solution", ""),
                    "descripcion": props.get("shortDescription", {}).get("problem", ""),
                    "accion": props.get("shortDescription", {}).get("solution", ""),
                    "ahorro_mensual_usd": props.get("extendedProperties", {}).get("savingsAmount", None),
                })
    return recomendaciones
