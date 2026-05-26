import httpx
from functools import lru_cache
from app.config import get_settings

settings = get_settings()

def _is_spanish(text: str) -> bool:
    markers = ("ó", "á", "é", "í", "ú", "ñ", "ción", "ización", "ú")
    return any(m in text for m in markers)

async def traducir_textos(textos: list[str]) -> list[str]:
    """
    Traduce una lista de textos al español.
    Omite los que ya están en español para no gastar caracteres.
    """
    # Identificar cuáles necesitan traducción
    indices_a_traducir = [
        i for i, t in enumerate(textos) if t and not _is_spanish(t)
    ]

    if not indices_a_traducir:
        return textos

    body = [{"text": textos[i]} for i in indices_a_traducir]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.azure_translator_endpoint}/translate",
            params={"api-version": "3.0", "to": "es"},
            headers={
                "Ocp-Apim-Subscription-Key": settings.azure_translator_key,
                "Ocp-Apim-Subscription-Region": settings.azure_translator_region,
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        traducciones = resp.json()

    # Reconstruir la lista original con las traducciones
    resultado = list(textos)
    for idx, traduccion in zip(indices_a_traducir, traducciones):
        resultado[idx] = traduccion["translations"][0]["text"]

    return resultado