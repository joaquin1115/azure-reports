import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/test")
os.environ.setdefault("AZURE_TENANT_ID", "tenant-test")
os.environ.setdefault("AZURE_CLIENT_ID", "client-test")
os.environ.setdefault("AZURE_CLIENT_SECRET", "secret-test")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("AZURE_TRANSLATOR_KEY", "translator-key-test")
os.environ.setdefault("AZURE_TRANSLATOR_ENDPOINT", "https://translator.example.com")
os.environ.setdefault("AZURE_TRANSLATOR_REGION", "eastus")
