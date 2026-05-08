import logging
import asyncio
import httpx
from datetime import datetime, timezone
from azure.functions import TimerRequest

# Runs every hour: 0 0 * * * *
async def _ejecutar():
    """
    Queries the backend for active schedules whose next_execution has passed,
    then invokes report generation for each one.
    """
    backend_url = "https://azurereport.azurewebsites.net/api"
    # In production, use Managed Identity or Key Vault to retrieve the function API key
    api_key = "FUNCTION_API_KEY"

    headers = {"x-functions-key": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=300) as client:
        # 1. Get active schedules due for execution
        resp = await client.get(f"{backend_url}/programaciones", headers=headers)
        if resp.status_code != 200:
            logging.error(f"Error al obtener programaciones: {resp.status_code} {resp.text}")
            return

        programaciones = resp.json()
        ahora = datetime.now(timezone.utc)

        due = [
            p for p in programaciones
            if p.get("activa") and
            datetime.fromisoformat(p["proxima_ejecucion"].replace("Z", "+00:00")) <= ahora
        ]

        logging.info(f"Programaciones a ejecutar: {len(due)}")

        for prog in due:
            await _generar_con_reintentos(client, backend_url, headers, prog)


async def _generar_con_reintentos(
    client: httpx.AsyncClient,
    backend_url: str,
    headers: dict,
    programacion: dict,
    max_intentos: int = 3,
):
    config_id = programacion["configuracion_id"]
    prog_id = programacion["id"]

    for intento in range(1, max_intentos + 1):
        try:
            resp = await client.post(
                f"{backend_url}/reportes",
                json={"configuracion_id": config_id},
                headers=headers,
            )
            if resp.status_code in (200, 202):
                logging.info(f"Reporte iniciado para programacion {prog_id} (intento {intento})")
                return
            else:
                logging.warning(
                    f"Intento {intento} fallido para programacion {prog_id}: "
                    f"{resp.status_code} {resp.text}"
                )
        except Exception as exc:
            logging.warning(f"Intento {intento} con excepción para programacion {prog_id}: {exc}")

        if intento < max_intentos:
            await asyncio.sleep(30 * intento)  # Exponential-ish backoff

    logging.error(f"Todos los intentos fallaron para programacion {prog_id}")


def main(timer: TimerRequest) -> None:
    if timer.past_due:
        logging.info("El timer está retrasado. Ejecutando igualmente.")
    logging.info(f"AzureReport Scheduler ejecutado a las {datetime.now(timezone.utc).isoformat()}")
    asyncio.run(_ejecutar())
