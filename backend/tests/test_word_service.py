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
