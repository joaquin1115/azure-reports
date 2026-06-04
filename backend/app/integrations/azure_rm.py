from dataclasses import dataclass

import httpx
from azure.identity.aio import ClientSecretCredential
from app.config import get_settings
from app.schemas.schemas import RecursoAzure
from app.models.models import TipoRecursoEnum

settings = get_settings()
ARM_TIMEOUT = httpx.Timeout(20.0, connect=5.0)

# Mapping Azure resource types → our enum
RESOURCE_TYPE_MAP = {
    "microsoft.compute/virtualmachines": TipoRecursoEnum.vm,
    "microsoft.sql/servers/databases": TipoRecursoEnum.db,
    "microsoft.web/serverfarms": TipoRecursoEnum.asp,
}

METRICS_BY_TYPE = {
    TipoRecursoEnum.vm: ["Percentage CPU", "Available Memory Percentage"],
    TipoRecursoEnum.db: ["dtu_consumption_percent"],
    TipoRecursoEnum.asp: ["CpuPercentage", "MemoryPercentage"],
}


@dataclass(frozen=True)
class AzureRMCredentials:
    tenant_id: str
    client_id: str
    client_secret: str


def _build_credentials(
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> AzureRMCredentials:
    """Builds Azure Resource Manager client-credential auth data."""
    return AzureRMCredentials(
        tenant_id=tenant_id or settings.azure_tenant_id,
        client_id=client_id or settings.azure_client_id,
        client_secret=client_secret or settings.azure_client_secret,
    )


async def _get_access_token(
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> str:
    """Gets an ARM token with tenant_id, client_id and client_secret only."""
    credentials = _build_credentials(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    credential = ClientSecretCredential(
        tenant_id=credentials.tenant_id,
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
    )
    try:
        token = await credential.get_token("https://management.azure.com/.default")
        return token.token
    finally:
        await credential.close()


async def listar_subscriptions_por_tenant(
    tenant_id: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[str]:
    """Lists enabled subscription IDs visible to the ARM service principal."""
    token = await _get_access_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    url = "https://management.azure.com/subscriptions?api-version=2020-01-01"
    subscription_ids: list[str] = []

    async with httpx.AsyncClient(timeout=ARM_TIMEOUT) as client:
        for attempt in range(2):
            try:
                resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("value", []):
                    state = item.get("state")
                    sub_id = item.get("subscriptionId")
                    if state == "Enabled" and sub_id:
                        subscription_ids.append(sub_id)
                break
            except httpx.ReadTimeout:
                if attempt == 1:
                    return []

    return subscription_ids


async def obtener_recursos_por_tenant(
    tenant_id: str,
    subscription_id: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[RecursoAzure]:
    """Fetches all supported resources from a subscription."""
    token = await _get_access_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resources?&api-version=2021-04-01"
    )
    recursos = []
    async with httpx.AsyncClient(timeout=ARM_TIMEOUT) as client:
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
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """
    Returns daily metric data for a resource over a given month.
    Result shape: { metric_name: { "values": [float], "dates": [str] } }
    """
    from datetime import datetime, timezone
    import calendar

    token = await _get_access_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    metrica_names = METRICS_BY_TYPE[tipo]

    last_day = calendar.monthrange(periodo_anio, periodo_mes)[1]

    start = (
        datetime(periodo_anio, periodo_mes, 1, tzinfo=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    end = (
        datetime(periodo_anio, periodo_mes, last_day, 23, 59, 59, tzinfo=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    resultado = {}

    async with httpx.AsyncClient(timeout=ARM_TIMEOUT) as client:
        for metrica in metrica_names:
            url = (
                f"https://management.azure.com{resource_id}"
                f"/providers/microsoft.insights/metrics"
                f"?api-version=2023-10-01"
                f"&metricnames={metrica}"
                f"&aggregation=Maximum,Minimum,Average"
                f"&interval=PT6H"
                f"&timespan={start}/{end}"
            )

            print(url)

            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"}
            )

            if resp.status_code != 200:
                print(resp.text)
                continue

            data = resp.json()
            print("data:", data)

            valores = []
            fechas = []

            for serie in data.get("value", []):
                for ts in serie.get("timeseries", []):
                    for dp in ts.get("data", []):
                        fechas.append(dp.get("timeStamp", ""))
                        valores.append(
                            dp.get("maximum")
                            or dp.get("average")
                            or 0.0
                        )

            resultado[metrica] = {
                "values": valores,
                "dates": fechas
            }

    return resultado


async def validar_tenant(
    tenant_id_azure: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> bool:
    """Checks that ARM can obtain a token for the tenant service principal."""
    try:
        await _get_access_token(
            tenant_id=tenant_id_azure,
            client_id=client_id,
            client_secret=client_secret,
        )
        return True
    except Exception:
        return False
