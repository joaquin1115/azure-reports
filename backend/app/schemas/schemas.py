from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from app.models.models import RolEnum, GravedadEnum, TipoRecursoEnum, EstadoReporteEnum


# ── Usuario ───────────────────────────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    correo: EmailStr
    nombre: str
    rol: RolEnum
    cliente_ids: list[int] = []


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolEnum] = None
    cliente_ids: Optional[list[int]] = None
    activo: Optional[bool] = None


class UsuarioOut(BaseModel):
    id: int
    correo: str
    nombre: str
    rol: RolEnum
    activo: bool
    creado_en: datetime
    clientes: list["ClienteSimple"] = []

    model_config = {"from_attributes": True}


# ── Cliente ───────────────────────────────────────────────────────────────────
class TenantCreate(BaseModel):
    tenant_id_azure: str
    nombre: str


class TenantOut(BaseModel):
    id: int
    tenant_id_azure: str
    nombre: str

    model_config = {"from_attributes": True}


class ClienteCreate(BaseModel):
    nombre: str
    tenants: list[TenantCreate]


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    tenants: Optional[list[TenantCreate]] = None
    activo: Optional[bool] = None


class ClienteSimple(BaseModel):
    id: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class ClienteOut(BaseModel):
    id: int
    nombre: str
    activo: bool
    creado_en: datetime
    tenants: list[TenantOut] = []

    model_config = {"from_attributes": True}


# ── Recurso Azure (no persistido, viene de Azure RM) ─────────────────────────
class RecursoAzure(BaseModel):
    resource_id: str
    nombre: str
    tipo: TipoRecursoEnum
    grupo_recursos: str
    tenant_id: str


# ── Configuracion ─────────────────────────────────────────────────────────────
class RecursoConfigCreate(BaseModel):
    resource_id_azure: str
    nombre: str
    tipo: TipoRecursoEnum


class ConfiguracionCreate(BaseModel):
    cliente_id: int
    nombre: str = "Reporte manual"
    periodo_mes: int
    periodo_anio: int
    gravedad: GravedadEnum = GravedadEnum.ambas
    guardada: bool = False
    recursos: list[RecursoConfigCreate]

    @field_validator("periodo_mes")
    @classmethod
    def validar_mes(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v


class RecursoConfigOut(BaseModel):
    id: int
    resource_id_azure: str
    nombre: str
    tipo: TipoRecursoEnum

    model_config = {"from_attributes": True}


class ConfiguracionOut(BaseModel):
    id: int
    cliente_id: int
    nombre: str
    periodo_mes: int
    periodo_anio: int
    gravedad: GravedadEnum
    guardada: bool
    creado_en: datetime
    recursos: list[RecursoConfigOut] = []

    model_config = {"from_attributes": True}


# ── Programacion ──────────────────────────────────────────────────────────────
class ProgramacionCreate(BaseModel):
    disparador_id: Optional[int] = None
    configuracion_id: Optional[int] = None
    fecha_inicio: datetime
    frecuencia: str = "Mensual"


class ProgramacionOut(BaseModel):
    id: int
    disparador_id: int
    fecha_inicio: datetime
    frecuencia: str
    proxima_ejecucion: datetime
    activa: bool
    creado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Reporte ───────────────────────────────────────────────────────────────────
class ReporteCreate(BaseModel):
    cliente_id: int
    periodo_mes: int
    periodo_anio: int
    gravedad: GravedadEnum = GravedadEnum.ambas
    recursos: list[RecursoConfigCreate]


class ReporteOut(BaseModel):
    id: int
    disparador_id: int
    usuario_id: int
    periodo_mes: int
    periodo_anio: int
    inicio_generacion: Optional[datetime]
    fin_generacion: Optional[datetime]
    tiempo_generacion_seg: Optional[float] = None
    url_docx: Optional[str]
    estado: EstadoReporteEnum | str
    creado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Update forward refs
UsuarioOut.model_rebuild()
