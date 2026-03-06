"""
Alpha-Guard — FastAPI Application
==================================
Forensic Credit Risk Analysis Platform

API Documentation: http://localhost:8000/docs
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else reads os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from risk_engine import router as risk_router
from scraper import router as data_router
from forensic_analyzer import router as forensic_router
from report_generator import router as report_router

# ──────────────────────────────────────────────
#  Application Setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="Alpha-Guard API",
    description=(
        "Professional-grade forensic credit risk analysis platform.\n\n"
        "**Features:**\n"
        "- Altman Z-Score calculation with component breakdown\n"
        "- Monte Carlo revenue simulation (placeholder)\n"
        "- SEC EDGAR 10-K data ingestion\n"
        "- Yahoo Finance fallback scraping\n"
        "- **Forensic AI Analysis** — Gemini-powered linguistic stress detection\n"
        "- Truth Score & Deception Alerts\n\n"
        "Built with FastAPI · Pandas · NumPy · Google Gemini"
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
#  Routers
# ──────────────────────────────────────────────

app.include_router(risk_router)
app.include_router(data_router)
app.include_router(forensic_router)
app.include_router(report_router)

# ──────────────────────────────────────────────
#  Root / Health Check
# ──────────────────────────────────────────────

@app.get(
    "/",
    tags=["System"],
    summary="Health Check",
    description="Returns the API status and version.",
)
async def root():
    return {
        "status": "operational",
        "platform": "Alpha-Guard",
        "version": "0.2.0",
        "modules": ["risk_engine", "data_ingestion", "forensic_ai"],
        "docs": "/docs",
    }
