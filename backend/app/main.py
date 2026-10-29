from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router

app = FastAPI(title="AI Video Generator")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

from pathlib import Path
from fastapi.staticfiles import StaticFiles
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():  # production: one port serves API + UI
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
