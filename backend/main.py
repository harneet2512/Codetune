"""CodeTune Backend — FastAPI orchestrator for demo + live mode."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, BACKEND_PORT
from routes.health import router as health_router
from routes.demo import router as demo_router
from routes.live import router as live_router
from routes.auth import router as auth_router

app = FastAPI(
    title="CodeTune Backend",
    description="Post-training lab orchestrator. Demo traces + live inference with real tool calls.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(demo_router, prefix="/api")
app.include_router(live_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)
