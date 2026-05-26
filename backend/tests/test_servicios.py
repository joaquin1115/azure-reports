import pytest
from app.services.analisis_service import analizar_metrica


# ── Motor de análisis ─────────────────────────────────────────────────────────

def test_recurso_subutilizado():
    valores = [5.0, 4.5, 3.0, 6.1, 5.5, 4.0, 3.5, 5.0, 6.0, 4.2,
               5.1, 3.8, 4.9, 5.0, 4.0, 3.0, 5.5, 4.8, 5.2, 4.1,
               3.9, 5.3, 4.7, 5.0, 4.2, 3.8, 5.1, 4.6, 5.0, 4.4]
    fechas = [f"2025-01-{i+1:02d}" for i in range(30)]
    resultado = analizar_metrica("Percentage CPU", valores, fechas)
    assert resultado.promedio < 10
    assert resultado.maximo < 30
    assert any("subutiliz" in o.lower() for o in resultado.observaciones)


def test_deteccion_anomalia():
    # Normal distribution around 30%, one spike at 95%
    valores = [30.0] * 14 + [95.0] + [30.0] * 15
    fechas = [f"2025-01-{i+1:02d}" for i in range(30)]
    resultado = analizar_metrica("Percentage CPU", valores, fechas)
    assert len(resultado.anomalias) >= 1
    assert resultado.anomalias[0]["valor"] == 95.0


def test_imputacion_nulos():
    valores_con_nulos = [50.0, None, 52.0, None, 48.0, 51.0, 50.5,
                         49.0, 51.5, 50.0, 52.5, 49.5, 50.0, 51.0,
                         50.5, 49.0, 50.5, 51.5, 50.0, 50.5, 49.5,
                         51.0, 50.0, 51.5, 49.0, 50.5, 51.0, 50.0,
                         50.5, 51.0]
    fechas = [f"2025-01-{i+1:02d}" for i in range(30)]
    resultado = analizar_metrica("Percentage CPU", valores_con_nulos, fechas)
    assert resultado.promedio > 0
    assert resultado.maximo > 0
    assert len(resultado.valores) == 30


def test_serie_vacia():
    resultado = analizar_metrica("Percentage CPU", [], [])
    assert resultado.promedio == 0
    assert "Sin datos" in resultado.observaciones[0]


def test_tendencia_creciente():
    # First half ~20%, second half ~50%
    valores = [20.0 + i * 0.5 for i in range(15)] + [45.0 + i * 0.5 for i in range(15)]
    fechas = [f"2025-01-{i+1:02d}" for i in range(30)]
    resultado = analizar_metrica("Percentage CPU", valores, fechas)
    assert any("tendencia creciente" in o.lower() for o in resultado.observaciones)


def test_estadisticos_correctos():
    valores = [10.0, 20.0, 30.0, 40.0, 50.0]
    fechas = [f"2025-01-{i+1:02d}" for i in range(5)]
    resultado = analizar_metrica("DTU Percentage", valores, fechas)
    assert resultado.minimo == 10.0
    assert resultado.maximo == 50.0
    assert resultado.promedio == 30.0
    