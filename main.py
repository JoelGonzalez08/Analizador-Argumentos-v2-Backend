"""
FastAPI Backend for Silogia Studio
Main application entry point
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import secrets
from dotenv import load_dotenv

from app.core.database import init_db
from app.api.routers import arguments, users, conversations

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_db()
    yield


# Configuración de documentación segura
DOCS_ENABLED = os.getenv("DOCS_ENABLED", "false").lower() == "true"
DOCS_USERNAME = os.getenv("DOCS_USERNAME", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD")

# Si los docs están habilitados pero no hay contraseña, generar advertencia
if DOCS_ENABLED and not DOCS_PASSWORD:
    print("WARNING: Docs are enabled but DOCS_PASSWORD is not set. Using a random password.")
    DOCS_PASSWORD = secrets.token_urlsafe(16)
    print(f"Generated DOCS_PASSWORD: {DOCS_PASSWORD}")


app = FastAPI(
    title="Silogia Studio API",
    description="API para análisis de argumentos y recomendaciones",
    version="1.0.0",
    lifespan=lifespan,
    # Deshabilitar docs automáticos - los implementaremos con protección
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# CORS configuration - Load allowed origins from environment variable
cors_origins_env = os.getenv("CORS_ORIGINS")

if not cors_origins_env:
    raise ValueError(
        "CORS_ORIGINS environment variable is not set. "
        "Please set it in your .env file with your frontend URL(s)."
    )

# Parse and clean origins
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

# Métodos permitidos específicos (más restrictivo que "*")
allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
# Headers permitidos específicos
allowed_headers = [
    "Content-Type",
    "Authorization",
    "Accept",
    "Origin",
    "X-Requested-With",
    "X-CSRF-Token"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers= allowed_headers,
    max_age=600,  # Cache preflight requests por 10 minutos
)


# Función de verificación de autenticación para docs
def verify_docs_credentials(request: Request) -> bool:
    """Verifica las credenciales para acceder a la documentación"""
    if not DOCS_ENABLED:
        return False
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return False
    
    try:
        scheme, credentials = auth_header.split()
        if scheme.lower() != "basic":
            return False
        
        import base64
        decoded = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
        
        return username == DOCS_USERNAME and password == DOCS_PASSWORD
    except Exception:
        return False


# Endpoints protegidos de documentación
@app.get("/docs", include_in_schema=False)
async def get_documentation(request: Request):
    """Documentación interactiva (Swagger UI) - Protegida con autenticación"""
    if not verify_docs_credentials(request):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Basic"},
        )
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Docs")


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(request: Request):
    """Documentación alternativa (ReDoc) - Protegida con autenticación"""
    if not verify_docs_credentials(request):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Basic"},
        )
    return get_redoc_html(openapi_url="/openapi.json", title="ReDoc")


@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(request: Request):
    """Schema OpenAPI - Protegido con autenticación"""
    if not verify_docs_credentials(request):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Could not validate credentials"},
            headers={"WWW-Authenticate": "Basic"},
        )
    return JSONResponse(get_openapi(title=app.title, version=app.version, routes=app.routes))

# Include routers
app.include_router(arguments.router, prefix="/api/arguments", tags=["arguments"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(conversations.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Silogia Studio API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
