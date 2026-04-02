"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# -- Mode --
DEFAULT_MODE = os.getenv("CODETUNE_MODE", "demo")  # "demo" or "live"

# -- HuggingFace --
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "")  # e.g. https://harneetbali-codetune-grpo.hf.space/api/predict
HF_TOKEN = os.getenv("HF_TOKEN", "")

# -- GitHub --
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# -- Google OAuth --
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# -- Server --
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORS_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
]

# -- Demo traces --
DEMO_TRACES_DIR = os.getenv("DEMO_TRACES_DIR", os.path.join(os.path.dirname(__file__), "..", "playground", "data"))
