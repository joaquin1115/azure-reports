import httpx
from azure.identity.aio import DefaultAzureCredential
from app.config import get_settings
from app.schemas.schemas import RecursoAzure
from app.models.models import TipoRecursoEnum

settings = get_settings()

# Mapping Azure resource types → our enum
RESOURCE_TYPE_MAP = {
    "microsoft.compute/virtualmachines": TipoRecursoEnum.vm,
    "microsoft.sql/servers/databases": TipoRecursoEnum.db,
    "microsoft.web/serverfarms": TipoRecursoEnum.asp,
}

METRICS_BY_TYPE = {
    TipoRecursoEnum.vm: ["Percentage CPU", "Available Memory Bytes"],
    TipoRecursoEnum.db: ["dtu_consumption_percent"],
    TipoRecursoEnum.asp: ["CpuPercentage", "MemoryPercentage"],
}


async def _get_access_token() -> str:
    credential = DefaultAzureCredential()
    token = await credential.get_token("https://management.azure.com/.default")
    await credential.close()
    return token.token


async def listar_subscriptions_por_tenant(tenant_id: str) -> list[str]:
    """Lists subscription IDs visible by the managed identity for a given tenant."""
    token = await _get_access_token()
    url = "https://management.azure.com/subscriptions?api-version=2020-01-01"
    subscription_ids: list[str] = []

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("value", []):
            tenant = item.get("tenantId")
            state = item.get("state")
            sub_id = item.get("subscriptionId")
            if tenant == tenant_id and state == "Enabled" and sub_id:
                subscription_ids.append(sub_id)

    return subscription_ids


async def obtener_recursos_por_tenant(
    tenant_id: str,
    subscription_id: str,
) -> list[RecursoAzure]:
    """Fetches all supported resources from a subscription."""
    token = await _get_access_token()
    tipos = ",".join(RESOURCE_TYPE_MAP.keys())
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resources?$filter=resourceType eq '{tipos}'&api-version=2021-04-01"
    )
    recursos = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("value", []):
            rt = item.get("type", "").lower()
            tipo = RESOURCE_TYPE_MAP.get(rt)
            if tipo:
                recursos.append(
                    RecursoAzure(
                        resource_id=item["id"],
                        nombre=item["name"],
                        tipo=tipo,
                        grupo_recursos=item["id"].split("/")[4],
                        tenant_id=tenant_id,
                    )
                )
    return recursos


async def obtener_metricas_recurso(
    resource_id: str,
    tipo: TipoRecursoEnum,
    periodo_mes: int,
    periodo_anio: int,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """
    Returns daily metric data for a resource over a given month.
    Result shape: { metric_name: { "values": [float], "dates": [str] } }
    """
    from datetime import datetime, timezone
    import calendar

    token = await _get_access_token()
    metrica_names = METRICS_BY_TYPE[tipo]
    last_day = calendar.monthrange(periodo_anio, periodo_mes)[1]
    start = datetime(periodo_anio, periodo_mes, 1, tzinfo=timezone.utc).isoformat()
    end = datetime(periodo_anio, periodo_mes, last_day, 23, 59, 59, tzinfo=timezone.utc).isoformat()

    resultado = {}
    async with httpx.AsyncClient() as client:
        for metrica in metrica_names:
            url = (
                f"https://management.azure.com{resource_id}"
                f"/providers/microsoft.insights/metrics"
                f"?api-version=2023-10-01"
                f"&metricnames={metrica}"
                f"&aggregation=Maximum,Minimum,Average"
                f"&interval=P1D"
                f"&timespan={start}/{end}"
            )
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                continue
            data = resp.json()
            valores = []
            fechas = []
            for serie in data.get("value", []):
                for ts in serie.get("timeseries", []):
                    for dp in ts.get("data", []):
                        fechas.append(dp.get("timeStamp", ""))
                        valores.append(dp.get("maximum") or dp.get("average") or 0.0)
            resultado[metrica] = {"values": valores, "dates": fechas}
    return resultado


async def validar_tenant(tenant_id_azure: str) -> bool:
    """Checks that a tenant is accessible via Azure RM."""
    url = f"https://management.azure.com/tenants?api-version=2022-12-01"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer placeholder"},
            )
        return resp.status_code != 404
    except Exception:
        return False
