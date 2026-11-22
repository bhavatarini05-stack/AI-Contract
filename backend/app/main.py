import logging
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app import jobs, scheduler
from app.api import admin, analysis, auth, contracts, integrations, obligations
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.llm import get_provider
from app.models import Policy, Template
from app.pipeline import handwriting, ocr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = Path(__file__).resolve().parent / "rules"


def seed_defaults() -> None:
    """Load the sample privacy policy and standard template on first run."""
    with SessionLocal() as db:
        if not db.scalar(select(func.count()).select_from(Policy)):
            data = yaml.safe_load(
                (RULES_DIR / "sample_privacy_policy.yaml").read_text(encoding="utf-8")
            )
            db.add(
                Policy(name=data["name"], description=data.get("description"), rules=data["rules"])
            )
        if not db.scalar(select(func.count()).select_from(Template)):
            for f in sorted((REPO_ROOT / "templates").glob("*.md")):
                db.add(
                    Template(
                        name=f.stem.replace("_", " ").title(),
                        contract_type="Service Agreement",
                        content=f.read_text(encoding="utf-8"),
                    )
                )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    seed_defaults()
    scheduler.start()
    yield
    scheduler.stop()
    jobs.shutdown()


app = FastAPI(
    title="AI Contract Analyzer",
    version="0.1.0",
    description="Contract analysis using free, local open-source models. Not legal advice.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_url, "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(contracts.router)
app.include_router(analysis.router)
app.include_router(obligations.router)
app.include_router(integrations.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    llm = get_provider().health()
    return {
        "status": "ok",
        "llm": llm,
        "ocr": {"tesseract": ocr.is_available(), "languages": get_settings().ocr_languages},
        "handwriting": {"trocr": handwriting.is_available()},
    }
