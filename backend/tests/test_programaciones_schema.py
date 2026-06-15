from datetime import datetime, timezone

from app.models.models import GravedadEnum
from app.schemas.schemas import ProgramacionCreate


def _programacion_payload(fecha_inicio: datetime) -> dict:
    return {
        "cliente_id": 1,
        "gravedad": GravedadEnum.ambas,
        "recursos": [],
        "fecha_inicio": fecha_inicio,
    }


def test_programacion_create_convierte_fecha_inicio_aware_a_utc_naive() -> None:
    programacion = ProgramacionCreate(**_programacion_payload(datetime(2026, 6, 15, 5, 0, tzinfo=timezone.utc)))

    assert programacion.fecha_inicio == datetime(2026, 6, 15, 5, 0)
    assert programacion.fecha_inicio.tzinfo is None


def test_programacion_create_mantiene_fecha_inicio_naive() -> None:
    fecha_inicio = datetime(2026, 6, 15, 5, 0)

    programacion = ProgramacionCreate(**_programacion_payload(fecha_inicio))

    assert programacion.fecha_inicio == fecha_inicio
    assert programacion.fecha_inicio.tzinfo is None
