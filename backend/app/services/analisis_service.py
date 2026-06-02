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
    desviacion: float
    anomalias: list[dict]
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
            desviacion=0,
            anomalias=[],
            observaciones=["Sin datos disponibles para el período."],
            valores=[],
            fechas=[],
        )

    # Imputación de nulos mediante mediana
    validos = [v for v in valores if v is not None]
    mediana = statistics.median(validos) if validos else 0

    valores_limpios = [
        v if v is not None else mediana
        for v in valores
    ]

    promedio = statistics.mean(valores_limpios)
    maximo = max(valores_limpios)
    minimo = min(valores_limpios)
    p95 = calcular_p95(valores_limpios)

    desviacion = (
        statistics.stdev(valores_limpios)
        if len(valores_limpios) > 1
        else 0
    )

    # Detección de anomalías mediante Z-Score
    anomalias = []

    if desviacion > 0:
        for i, valor in enumerate(valores_limpios):

            z_score = abs(
                (valor - promedio) / desviacion
            )

            if z_score > 2.0:
                anomalias.append({
                    "fecha": fechas[i] if i < len(fechas) else f"Día {i+1}",
                    "valor": round(valor, 2),
                    "z_score": round(z_score, 2),
                })

    observaciones = _generar_observaciones(
        nombre=nombre,
        maximo=maximo,
        p95=p95,
        anomalias=anomalias,
        valores=valores_limpios,
    )

    return ResultadoMetrica(
        nombre=nombre,
        promedio=round(promedio, 2),
        maximo=round(maximo, 2),
        minimo=round(minimo, 2),
        p95=round(p95, 2),
        desviacion=round(desviacion, 2),
        anomalias=anomalias,
        observaciones=observaciones,
        valores=valores_limpios,
        fechas=fechas,
    )


def _generar_observaciones(
    nombre: str,
    maximo: float,
    p95: float,
    anomalias: list[dict],
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