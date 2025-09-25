"""
FastAPI application for AI Movie Task Service
Follows constitutional requirements for service-first architecture
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime
from .config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title="AI Movie Platform - Task Service API",
    description="Standalone GPU-intensive task processing service for AI movie production",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with structured logging"""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled errors"""
    logger.error(
        "Unhandled exception occurred",
        exception=str(exc),
        path=str(request.url.path),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# Health check endpoint (no authentication required)
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for service monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# Import and include API routers (will be implemented in later tasks)
try:
    from .api import tasks, projects, workers
    
    # Include API routers
    app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
    app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
    app.include_router(workers.router, prefix="/api/v1", tags=["workers"])
    
except ImportError:
    # API modules not yet implemented, that's expected during testing phase
    logger.info("API modules not yet implemented - running in development mode")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(
        "AI Movie Task Service starting up",
        environment=settings.environment,
        api_port=settings.api_port,
        debug=settings.debug,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("AI Movie Task Service shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers,
    )