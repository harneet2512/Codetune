"""FastAPI application for the ToolTune playground."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from playground.api.routes import router

app = FastAPI(title="ToolTune Playground")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.mount("/", StaticFiles(directory="playground/static", html=True), name="static")
