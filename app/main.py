"""
ProbioMatrix — API Principal (FastAPI)

Sistema de recomendação probiótica inteligente que integra:
- BacDive (bacdive.dsmz.de) — metadados bacterianos
- Probio-Ichnos — dados probióticos curados
- Gemini AI — síntese harmônica de recomendações

Inspirado na abordagem NotCo de mapeamento inteligente de matrizes alimentares.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import consumers, recommendations, search

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação."""
    settings = get_settings()
    logger.info("🧬 ProbioMatrix iniciando...")
    logger.info("   Gemini model: %s", settings.gemini_model)
    logger.info("   BacDive API: %s", "configurado" if settings.bacdive_email else "não configurado")
    logger.info("   Gemini API: %s", "configurada" if settings.gemini_api_key else "não configurada (modo fallback)")
    yield
    logger.info("🧬 ProbioMatrix encerrado.")


app = FastAPI(
    title="🧬 ProbioMatrix API",
    description=(
        "Sistema inteligente de recomendação probiótica que integra dados de "
        "múltiplos bancos (BacDive, Probio-Ichnos) e usa IA (Gemini) para "
        "gerar recomendações personalizadas de cepas probióticas em matrizes "
        "alimentares preferidas pelo usuário."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (permitir Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(search.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(consumers.router, prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    """Health check e informações do sistema."""
    settings = get_settings()
    return {
        "name": "ProbioMatrix API",
        "version": "1.0.0",
        "status": "online",
        "sources": {
            "bacdive": "configured" if settings.bacdive_email else "not_configured",
            "probio_ichnos": "local_curated_data",
            "gemini_ai": "configured" if settings.gemini_api_key else "fallback_mode",
        },
        "docs": "/docs",
        "endpoints": {
            "search_strains": "POST /api/search/strains",
            "list_strains": "GET /api/search/strains",
            "search_foods": "GET /api/search/foods",
            "recommendations": "POST /api/recommendations",
            "consumer_insights": "GET /api/consumers/insights",
            "synthetic_test": "GET /api/consumers/synthetic-test",
        },
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


# ── Executar diretamente ──────────────────────────────
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
