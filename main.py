"""
FastAPI Backend for Silogia Studio
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
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


app = FastAPI(
    title="Silogia Studio API",
    description="API para análisis de argumentos y recomendaciones",
    version="1.0.0",
    lifespan=lifespan
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
