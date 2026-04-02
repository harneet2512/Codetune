"""Health check and status endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "codetune-backend", "version": "1.0.0"}


@router.get("/api/status")
async def status():
    """Return backend status including model and connector readiness."""
    return {
        "mode": "demo",
        "model_endpoint": "not_configured",
        "connectors": {
            "github": "ready",
            "gmail": "not_connected",
            "drive": "not_connected",
        },
    }
