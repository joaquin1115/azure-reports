from app.services.word_service import _consolidar_recomendaciones


def test_consolidar_recomendaciones_normaliza_listas_para_claves_hashables() -> None:
    recomendaciones = [
        {
            "categoria": "Cost",
            "impacto": "High",
            "descripcion": ["Problema traducido"],
            "accion": ["Acción traducida"],
            "recurso": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/sites/app-1",
        },
        {
            "categoria": "Cost",
            "impacto": "High",
            "descripcion": ["Problema traducido"],
            "accion": ["Acción traducida"],
            "recurso": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Web/sites/app-2",
        },
    ]

    assert _consolidar_recomendaciones(recomendaciones) == [
        {
            "categoria": "Cost",
            "impacto": "High",
            "descripcion": "Problema traducido",
            "accion": "Acción traducida",
            "recursos": ["app-1", "app-2"],
        }
    ]


def test_generar_word_usa_observaciones_y_titulos_metricas_en_tabla() -> None:
    import io

    from docx import Document

    from app.services.analisis_service import ResultadoMetrica
    from app.services.word_service import generar_word

    cpu = ResultadoMetrica(
        nombre="Percentage CPU",
        promedio=20,
        maximo=40,
        minimo=10,
        p95=35,
        observaciones=["Observación: performance estable."],
        valores=[10, 20, 40],
        fechas=["2026-06-01", "2026-06-02", "2026-06-03"],
    )
    memoria = ResultadoMetrica(
        nombre="MemoryPercentage",
        promedio=70,
        maximo=95,
        minimo=50,
        p95=90,
        observaciones=["Observación: performance con picos de uso."],
        valores=[50, 70, 95],
        fechas=["2026-06-01", "2026-06-02", "2026-06-03"],
    )

    word = generar_word(
        cliente_nombre="Cliente",
        periodo_mes=6,
        periodo_anio=2026,
        usuario_nombre="Usuario",
        recomendaciones=[],
        resultados_por_recurso=[
            {
                "tipo": "VM",
                "nombre": "vm-01",
                "metricas": [cpu, memoria],
            }
        ],
    )

    doc = Document(io.BytesIO(word))
    tabla = doc.tables[0]

    encabezados = [cell.text for cell in tabla.rows[0].cells]
    detalle = tabla.rows[1].cells[3].text

    assert encabezados == [
        "Recurso",
        "Porcentaje de Uso de CPU (Mínimo – Máximo)",
        "Porcentaje de Uso de Memoria RAM (Mínimo – Máximo)",
        "Detalle del rendimiento",
    ]
    assert "Métrica principal" not in encabezados[1]
    assert "Métrica secundaria" not in encabezados[2]
    assert "Porcentaje de Uso de CPU: Observación: performance estable." in detalle
    assert "Porcentaje de Uso de Memoria RAM: Observación: performance con picos de uso." in detalle
