import httpx
from functools import lru_cache
from app.core.config import settings  # ajusta al import de tu config

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
            f"{settings.AZURE_TRANSLATOR_ENDPOINT}/translate",
            params={"api-version": "3.0", "to": "es"},
            headers={
                "Ocp-Apim-Subscription-Key": settings.AZURE_TRANSLATOR_KEY,
                "Ocp-Apim-Subscription-Region": settings.AZURE_TRANSLATOR_REGION,
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