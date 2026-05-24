from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import (
    generate_blob_sas,
    BlobSasPermissions,
    ContentSettings,
)
from datetime import datetime, timedelta, timezone
from app.config import get_settings
import uuid

settings = get_settings()


async def subir_pdf(pdf_bytes: bytes, nombre_blob: str) -> str:
    """Uploads PDF bytes to Blob Storage and returns the blob name."""

    async with BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    ) as service:

        container = service.get_container_client(
            settings.azure_storage_container
        )

        try:
            await container.create_container()
        except Exception:
            pass

        blob = container.get_blob_client(nombre_blob)

        await blob.upload_blob(
            pdf_bytes,
            overwrite=True,
            content_settings=ContentSettings(
                content_type="application/pdf"
            ),
        )

    return nombre_blob


async def generar_sas_url(
    nombre_blob: str,
    expiry_hours: int = 24
) -> str:
    """Generates a time-limited SAS URL for downloading a PDF."""

    from azure.storage.blob import BlobServiceClient as SyncClient

    sync_client = SyncClient.from_connection_string(
        settings.azure_storage_connection_string
    )

    account_name = sync_client.account_name
    account_key = sync_client.credential.account_key

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.azure_storage_container,
        blob_name=nombre_blob,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc)
        + timedelta(hours=expiry_hours),
    )

    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{settings.azure_storage_container}/"
        f"{nombre_blob}?{sas_token}"
    )