from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timezone
from typing import Optional
from app.models.models import RolEnum, GravedadEnum, TipoRecursoEnum, EstadoReporteEnum


TIPO_RECOMENDACION_LABELS = {
    GravedadEnum.alta: "Alta",
    GravedadEnum.media: "Alta y media",
    GravedadEnum.ambas: "Alta, media y baja",
}


class UsuarioCreate(BaseModel):
    correo: EmailStr
    nombre: str
    rol: RolEnum


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolEnum] = None
    activo: Optional[bool] = None


class UsuarioOut(BaseModel):
    id: int
    correo: str
    nombre: str
    rol: RolEnum
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


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


class RecursoAzure(BaseModel):
    resource_id: str
    nombre: str
    tipo: TipoRecursoEnum
    grupo_recursos: str
    tenant_id: str


class RecursoSeleccionado(BaseModel):
    resource_id_azure: str
    nombre: str | None = None
    tipo: TipoRecursoEnum | None = None


class RecursoDisparadorOut(BaseModel):
    id: int
    azure_resource_id: str
    nombre: str


class ReporteBaseCreate(BaseModel):
    cliente_id: int
    gravedad: GravedadEnum = GravedadEnum.ambas
    recursos: list[RecursoSeleccionado]


class ReporteCreate(ReporteBaseCreate):
    periodo_mes: int
    periodo_anio: int

    @field_validator("periodo_mes")
    @classmethod
    def validar_mes(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("El mes debe estar entre 1 y 12")
        return v


class ProgramacionCreate(ReporteBaseCreate):
    fecha_inicio: datetime
    frecuencia: str = "Mensual"

    @field_validator("fecha_inicio")
    @classmethod
    def normalizar_fecha_inicio(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v
        return v.astimezone(timezone.utc).replace(tzinfo=None)


class ProgramacionOut(BaseModel):
    id: int
    cliente: ClienteSimple
    tipo_recomendacion: str
    frecuencia: str
    proxima_ejecucion: Optional[datetime]
    activa: bool
    creado_en: datetime
    recursos: list[RecursoDisparadorOut] = []


class ReporteOut(BaseModel):
    id: int
    disparador_id: int
    usuario_id: int
    cliente: ClienteSimple
    periodo_mes: int
    periodo_anio: int
    inicio_generacion: Optional[datetime]
    fin_generacion: Optional[datetime]
    tiempo_generacion_seg: Optional[float] = None
    url_docx: Optional[str]
    estado: EstadoReporteEnum | str
    tipo_recomendacion: str
    recurrencia: str
    error_mensaje: Optional[str]
    recursos: list[RecursoDisparadorOut] = []
    creado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}
