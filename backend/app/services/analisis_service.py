import statistics
from dataclasses import dataclass


@dataclass
class ResultadoMetrica:
    nombre: str
    promedio: float
    maximo: float
    minimo: float
    desviacion: float
    anomalias: list[dict]  # [{fecha, valor, z_score}]
    observaciones: list[str]
    valores: list[float]
    fechas: list[str]


def analizar_metrica(nombre: str, valores: list[float], fechas: list[str]) -> ResultadoMetrica:
    if not valores:
        return ResultadoMetrica(
            nombre=nombre, promedio=0, maximo=0, minimo=0,
            desviacion=0, anomalias=[], observaciones=["Sin datos disponibles para el período."],
            valores=[], fechas=[],
        )

    # Impute nulls with median
    validos = [v for v in valores if v is not None]
    mediana = statistics.median(validos) if validos else 0
    valores_limpios = [v if v is not None else mediana for v in valores]

    promedio = statistics.mean(valores_limpios)
    maximo = max(valores_limpios)
    minimo = min(valores_limpios)
    desviacion = statistics.stdev(valores_limpios) if len(valores_limpios) > 1 else 0

    # Z-score anomaly detection (threshold = 2.0)
    anomalias = []
    if desviacion > 0:
        for i, v in enumerate(valores_limpios):
            z = abs((v - promedio) / desviacion)
            if z > 2.0:
                anomalias.append({
                    "fecha": fechas[i] if i < len(fechas) else f"Día {i+1}",
                    "valor": round(v, 2),
                    "z_score": round(z, 2),
                })

    observaciones = _generar_observaciones(nombre, promedio, maximo, minimo, anomalias, valores_limpios)

    return ResultadoMetrica(
        nombre=nombre,
        promedio=round(promedio, 2),
        maximo=round(maximo, 2),
        minimo=round(minimo, 2),
        desviacion=round(desviacion, 2),
        anomalias=anomalias,
        observaciones=observaciones,
        valores=valores_limpios,
        fechas=fechas,
    )


def _generar_observaciones(
    nombre: str,
    promedio: float,
    maximo: float,
    minimo: float,
    anomalias: list[dict],
    valores: list[float],
) -> list[str]:
    obs = []
    metrica_lower = nombre.lower()

    # Subutilización
    if "cpu" in metrica_lower or "percentage" in metrica_lower:
        if promedio < 10 and maximo < 30:
            obs.append(
                f"El recurso presenta un promedio de {promedio:.1f}% con un máximo de {maximo:.1f}%, "
                f"lo que indica subutilización sostenida. Se recomienda evaluar el redimensionamiento."
            )
        elif promedio > 80:
            obs.append(
                f"El promedio de {promedio:.1f}% indica alta utilización. "
                f"Se recomienda evaluar el escalado del recurso."
            )
        else:
            obs.append(
                f"La métrica {nombre} se mantuvo en un promedio de {promedio:.1f}% "
                f"(mín: {minimo:.1f}%, máx: {maximo:.1f}%), dentro de rangos normales de operación."
            )

    # Anomalías
    if anomalias:
        fechas_anomalia = ", ".join(a["fecha"][:10] for a in anomalias[:3])
        obs.append(
            f"Se detectaron {len(anomalias)} valor(es) anómalos en las fechas: {fechas_anomalia}. "
            f"Se recomienda revisar los eventos ocurridos en dichos días."
        )

    # Tendencia creciente
    if len(valores) >= 6:
        mitad = len(valores) // 2
        primera = statistics.mean(valores[:mitad])
        segunda = statistics.mean(valores[mitad:])
        if segunda > primera * 1.2:
            obs.append(
                f"Se observa una tendencia creciente en la métrica {nombre}: "
                f"el promedio de la segunda mitad del período ({segunda:.1f}%) supera en más del 20% "
                f"al de la primera mitad ({primera:.1f}%)."
            )

    return obs if obs else [f"La métrica {nombre} no presenta observaciones relevantes para el período analizado."]
