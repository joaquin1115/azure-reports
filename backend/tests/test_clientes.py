import pytest
from fastapi import HTTPException, status

from app.routers.clientes import _validar_tenants_unicos
from app.schemas.schemas import TenantCreate


def test_validar_tenants_unicos_permite_tenants_distintos() -> None:
    _validar_tenants_unicos([
        TenantCreate(tenant_id_azure="tenant-a", nombre="Default"),
        TenantCreate(tenant_id_azure="tenant-b", nombre="Producción"),
    ])


def test_validar_tenants_unicos_rechaza_duplicados_en_el_mismo_cliente() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validar_tenants_unicos([
            TenantCreate(tenant_id_azure="tenant-a", nombre="Default"),
            TenantCreate(tenant_id_azure="tenant-a", nombre="Duplicado"),
        ])

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
