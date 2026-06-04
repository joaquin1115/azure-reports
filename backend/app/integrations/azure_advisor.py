import httpx
from app.models.models import GravedadEnum
from app.integrations.azure_rm import _get_access_token
from app.integrations.azure_translator import traducir_textos

GRAVEDAD_MAP = {
    GravedadEnum.alta: ["High"],
    GravedadEnum.media: ["Medium"],
    GravedadEnum.ambas: ["High", "Medium"],
}


async def obtener_recomendaciones(
    subscription_id: str,
    gravedad: GravedadEnum,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict]:
    token = await _get_access_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    niveles = GRAVEDAD_MAP[gravedad]
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/providers/Microsoft.Advisor/recommendations?api-version=2023-01-01"
    )
    recomendaciones = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Language": "es",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("value", []):
            props = item.get("properties", {})
            nivel = props.get("impact", "")
            if nivel in niveles:
                ahorro_raw = props.get("extendedProperties", {}).get("savingsAmount")
                try:
                    ahorro_mensual = float(ahorro_raw) if ahorro_raw is not None else 0
                except (ValueError, TypeError):
                    ahorro_mensual = 0

                short_description = props.get("shortDescription", {})

                recomendaciones.append({
                    "id": item.get("id"),
                    "categoria": props.get("category", ""),
                    "impacto": nivel,
                    "recurso": props.get("resourceMetadata", {}).get("resourceId", ""),
                    "nombre_recurso": props.get("resourceMetadata", {}).get("resourceName", ""),
                    "descripcion": short_description.get("problem", ""),
                    "accion": short_description.get("solution", ""),
                    "ahorro_mensual_usd": ahorro_mensual,
                })

    if recomendaciones:
        descripciones = [r["descripcion"] for r in recomendaciones]
        acciones = [r["accion"] for r in recomendaciones]

        descripciones_es = await traducir_textos(descripciones)
        acciones_es = await traducir_textos(acciones)

        for rec, desc, accion in zip(recomendaciones, descripciones_es, acciones_es):
            rec["descripcion"] = desc
            rec["accion"] = accion

    return recomendaciones
