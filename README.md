# AzureReport

Sistema web para la automatización de reportes de consumo de Azure — G&S.

## Estructura del proyecto

```
azurereport/
├── backend/              FastAPI (Python 3.12)
│   ├── app/
│   │   ├── auth/         Validación JWT Azure Entra ID
│   │   ├── db/           SQLAlchemy async + sesión
│   │   ├── integrations/ Azure RM, Advisor, Blob Storage
│   │   ├── models/       Modelos SQLAlchemy
│   │   ├── routers/      Endpoints REST
│   │   ├── schemas/      Pydantic schemas
│   │   ├── services/     Lógica de negocio (análisis, PDF, reporte)
│   │   └── main.py       Entry point FastAPI
│   ├── alembic/          Migraciones de BD
│   ├── tests/            Pruebas unitarias
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             React 18 + TypeScript + Ant Design
│   ├── src/
│   │   ├── components/   AppLayout, NotificacionFlotante
│   │   ├── pages/        GenerarReporte, Historial, Programar, Usuarios, Clientes
│   │   ├── services/     apiClient (Axios+MSAL), sseService, authConfig
│   │   ├── store/        Zustand (usuario, notificaciones)
│   │   └── styles/       global.css (colores institucionales)
│   └── package.json
├── function_app/         Azure Function (timer trigger)
│   ├── timer_trigger.py
│   └── function.json
└── .github/workflows/    CI/CD con GitHub Actions
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
