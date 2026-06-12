import statistics
from dataclasses import dataclass


UMBRAL_ALTA_UTILIZACION = 90


@dataclass
class ResultadoMetrica:
    nombre: str
    promedio: float
    maximo: float
    minimo: float
    p95: float
    observaciones: list[str]
    valores: list[float]
    fechas: list[str]


def calcular_p95(valores: list[float]) -> float:
    if not valores:
        return 0

    ordenados = sorted(valores)
    indice = int(0.95 * (len(ordenados) - 1))
    return ordenados[indice]


def analizar_metrica(
    nombre: str,
    valores: list[float],
    fechas: list[str]
) -> ResultadoMetrica:

    if not valores:
        return ResultadoMetrica(
            nombre=nombre,
            promedio=0,
            maximo=0,
            minimo=0,
            p95=0,
            observaciones=["Sin datos disponibles para el período."],
            valores=[],
            fechas=[],
        )

    valores_limpios = [v for v in valores if v is not None]

    promedio = statistics.mean(valores_limpios)
    maximo = max(valores_limpios)
    minimo = min(valores_limpios)
    p95 = calcular_p95(valores_limpios)

    observaciones = _generar_observaciones(
        nombre=nombre,
        maximo=maximo,
        p95=p95,
        valores=valores_limpios,
    )

    return ResultadoMetrica(
        nombre=nombre,
        promedio=round(promedio, 2),
        maximo=round(maximo, 2),
        minimo=round(minimo, 2),
        p95=round(p95, 2),
        observaciones=observaciones,
        valores=valores_limpios,
        fechas=fechas,
    )


def _generar_observaciones(
    nombre: str,
    maximo: float,
    p95: float,
    valores: list[float],
) -> list[str]:

    observaciones = []

    # =====================================================
    # Clasificación principal (criterio de la tesis)
    # =====================================================

    if maximo < UMBRAL_ALTA_UTILIZACION:

        observaciones.append(
            # f"El valor máximo registrado fue de {maximo:.1f}%, "
            # f"sin superar el umbral de alta utilización del "
            # f"{UMBRAL_ALTA_UTILIZACION}%. "
            f"Observación: performance estable."
        )

    elif p95 < UMBRAL_ALTA_UTILIZACION:

        observaciones.append(
            # f"Se registraron valores de utilización superiores al "
            # f"{UMBRAL_ALTA_UTILIZACION}% (máximo: {maximo:.1f}%), "
            # f"pero el percentil 95 fue de {p95:.1f}%, lo que indica "
            # f"que dichos eventos no representan el comportamiento "
            # f"habitual del recurso. "
            f"Observación: performance con picos de uso."
        )

    else:

        observaciones.append(
            # f"El valor máximo ({maximo:.1f}%) y el percentil 95 "
            # f"({p95:.1f}%) superan el umbral de "
            # f"{UMBRAL_ALTA_UTILIZACION}%, indicando que el recurso "
            # f"opera habitualmente en niveles elevados de utilización. "
            f"Observación: performance al tope de capacidad."
        )

    return observaciones