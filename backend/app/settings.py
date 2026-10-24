from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("HIDANI_DATA_DIR", PROJECT_ROOT / "backend" / "data"))
RESUME_DIR = DATA_DIR / "resumes"
MAX_RESUME_BYTES = 10 * 1024 * 1024
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8001"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8443,http://localhost:8444,http://127.0.0.1:8443,http://127.0.0.1:8444",
    ).split(",")
    if origin.strip()
]
