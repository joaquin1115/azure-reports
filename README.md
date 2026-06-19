# AzureReport

Sistema web para la automatización de reportes de consumo de Azure — G&S.

## Estructura del proyecto

```
azurereport/
├── backend/                        Backend FastAPI (Python 3.12)
│   ├── app/
│   │   ├── auth/
│   │   │   └── dependencies.py     Validación JWT Entra ID y control de roles
│   │   ├── db/
│   │   │   ├── catalog.py          Resolución de catálogos de BD
│   │   │   └── session.py          Motor async SQLAlchemy y generador de sesión
│   │   ├── integrations/
│   │   │   ├── azure_advisor.py    Cliente Azure Advisor REST API
│   │   │   ├── azure_rm.py         Cliente Azure Resource Manager y métricas
│   │   │   ├── azure_translator.py Cliente Azure Translator
│   │   │   └── blob_storage.py     Cliente Azure Blob Storage (upload + SAS URL)
│   │   ├── models/
│   │   │   └── models.py           Modelos SQLAlchemy de dominio
│   │   ├── routers/
│   │   │   ├── clientes.py         Endpoints CRUD de clientes y obtención de recursos
│   │   │   ├── programaciones.py   Endpoints de programaciones automáticas
│   │   │   ├── reportes.py         Endpoints de generación, SSE e historial
│   │   │   └── usuarios.py         Endpoints CRUD de usuarios
│   │   ├── schemas/
│   │   │   └── schemas.py          Schemas Pydantic de entrada y salida
│   │   ├── services/
│   │   │   ├── analisis_service.py Estadísticos y detección de consumo elevado
│   │   │   ├── grafico_service.py  Generación de gráficos con matplotlib
│   │   │   ├── reporte_service.py  Orquestador de generación y canal SSE
│   │   │   └── word_service.py     Generación de reportes DOCX
│   │   ├── config.py               Configuración centralizada con pydantic-settings
│   │   └── main.py                 Entry point FastAPI, CORS y registro de routers
│   ├── alembic/
│   │   ├── versions/               Archivos de migración generados por Alembic
│   │   └── env.py                  Configuración async de Alembic
│   ├── tests/                      Pruebas unitarias y de integración del backend
│   ├── alembic.ini                 Configuración de Alembic
│   ├── Dockerfile                  Imagen Docker para despliegue en App Service
│   ├── requirements.txt            Dependencias Python del backend
│   └── .env.example                Plantilla de variables de entorno
│
├── frontend/                       Frontend React 18 + TypeScript + Ant Design
│   ├── src/
│   │   ├── components/
│   │   │   ├── AppLayout.tsx       Layout raíz con sidebar y navegación por rol
│   │   │   └── NotificacionFlotante.tsx  Alerta flotante integrada con SSE
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx       Página de inicio de sesión con Microsoft (MSAL)
│   │   │   ├── GenerarReportePage.tsx    Wizard de generación de reportes (CU-01)
│   │   │   ├── ProgramarReportePage.tsx  Programación de reportes automáticos (CU-02)
│   │   │   ├── HistorialPage.tsx   Historial y descarga de reportes (CU-03)
│   │   │   ├── UsuariosPage.tsx    Gestión de usuarios con modal (CU-04)
│   │   │   └── ClientesPage.tsx    Gestión de clientes y tenants (CU-05)
│   │   ├── services/
│   │   │   ├── authConfig.ts       Configuración MSAL (clientId, tenantId, scopes)
│   │   │   ├── apiClient.ts        Instancia Axios con interceptor de token JWT
│   │   │   └── sseService.ts       Suscripción a Server-Sent Events por reporte
│   │   ├── store/
│   │   │   └── store.ts            Stores Zustand (usuario autenticado, notificaciones)
│   │   ├── styles/
│   │   │   └── global.css          Variables CSS, colores institucionales y layout
│   │   ├── staticwebapp.config.json Configuración de rutas para Azure Static Web Apps
│   │   └── main.tsx                Entry point React con MSAL, Router y Ant Design
│   ├── index.html                  Documento HTML raíz de Vite
│   ├── package.json                Dependencias y scripts npm
│   ├── vite.config.ts              Configuración de Vite con proxy al backend
│   ├── tsconfig.json               Configuración TypeScript
│   ├── tsconfig.node.json          Configuración TypeScript para Vite/Node
│   └── .env.example                Plantilla de variables de entorno Vite
│
├── function_app/                   Azure Function (timer trigger)
│   ├── timer_trigger.py            Lógica del scheduler: consulta programaciones e invoca backend
│   └── function.json               Configuración del trigger (CRON: cada hora)
│
├── docs/
│   ├── diagramas_arquitectura.puml Diagramas PlantUML de componentes y despliegue
│   └── diagramas_secuencia.puml    Diagramas PlantUML de casos de uso
│
├── .github/
│   └── workflows/
│       └── deploy.yml              Pipeline CI/CD: test, build Docker, deploy Azure
│
└── README.md                       Instrucciones de configuración y despliegue
```

## Requisitos previos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Cuenta Azure con App Registration en Entra ID
- Azure Storage Account
- Azure App Service (para producción)

## Configuración inicial

### 1. App Registration en Azure Entra ID

1. Ve a **Azure Portal → Entra ID → App registrations → New registration**
2. Nombre: `AzureReport`
3. Redirect URI: `http://localhost:5173` (desarrollo) y tu URL de producción
4. En **Expose an API**: agrega el scope `access_as_user`
5. En **App roles**: crea los roles `admin` y `especialista`
6. Copia el **Client ID** y el **Tenant ID**

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edita .env con tus credenciales

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Crear base de datos
createdb azurereport

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`
Documentación: `http://localhost:8000/api/docs`

### 3. Frontend

```bash
cd frontend
cp .env.example .env
# Edita .env con tu CLIENT_ID y TENANT_ID

npm install
npm run dev
```

La app estará disponible en `http://localhost:5173`

### 4. Pruebas (backend)

```bash
cd backend
pytest tests/ -v
```

## Variables de entorno

### Backend (`.env`)

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL de conexión PostgreSQL async |
| `AZURE_TENANT_ID` | Tenant ID usado para emitir tokens de Azure Resource Manager con client credentials |
| `AZURE_CLIENT_ID` | Client ID usado para Azure Resource Manager con client credentials |
| `AZURE_CLIENT_SECRET` | Client secret usado para Azure Resource Manager con client credentials |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string de Azure Blob Storage |
| `AZURE_STORAGE_CONTAINER` | Nombre del contenedor de PDFs |
| `ALLOWED_ORIGINS` | Lista JSON de orígenes CORS permitidos |

### Frontend (`.env`)

| Variable | Descripción |
|---|---|
| `VITE_AZURE_CLIENT_ID` | Client ID del App Registration |
| `VITE_AZURE_TENANT_ID` | Tenant ID del App Registration |
| `VITE_API_URL` | URL base de la API backend |

## Despliegue en Azure

El pipeline de GitHub Actions (`.github/workflows/deploy.yml`) realiza automáticamente:

1. Ejecuta las pruebas del backend
2. Construye y publica la imagen Docker en Azure Container Registry
3. Despliega el backend en Azure App Service
4. Construye el frontend React
5. Despliega el frontend en Azure Static Web Apps

### Secrets requeridos en GitHub

| Secret | Descripción |
|---|---|
| `ACR_LOGIN_SERVER` | URL del Azure Container Registry |
| `ACR_USERNAME` | Usuario del ACR |
| `ACR_PASSWORD` | Contraseña del ACR |
| `AZURE_WEBAPP_NAME` | Nombre del App Service |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Publish profile del App Service |
| `AZURE_CREDENTIALS` | Credenciales JSON para actualizar App Settings del App Service |
| `DATABASE_URL` | URL de conexión PostgreSQL async para producción |
| `AZURE_TENANT_ID` | Tenant ID usado por backend/API y Azure Resource Manager con client credentials |
| `AZURE_CLIENT_ID` | Client ID usado por backend/API y Azure Resource Manager con client credentials |
| `AZURE_CLIENT_SECRET` | Client secret usado por Azure Resource Manager con client credentials |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string de Azure Blob Storage |
| `AZURE_STORAGE_CONTAINER` | Nombre del contenedor de PDFs |
| `AZURE_TRANSLATOR_KEY` | Key de Azure Translator |
| `AZURE_TRANSLATOR_ENDPOINT` | Endpoint de Azure Translator |
| `AZURE_TRANSLATOR_REGION` | Región de Azure Translator |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Token de Azure Static Web Apps |
| `VITE_AZURE_CLIENT_ID` | Client ID para el build del frontend |
| `VITE_AZURE_TENANT_ID` | Tenant ID para el build del frontend |
| `VITE_API_URL` | URL de la API en producción |

## Colores institucionales

| Color | Hex |
|---|---|
| Azul institucional (primario) | `#1987af` |
| Amarillo institucional (secundario) | `#ffbe1e` |
