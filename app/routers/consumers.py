"""Router de consumidores — insights reais (Amazon Reviews 2023) e seed de teste (Faker)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models import ConsumerInsightsResponse
from app.services.consumer_insights import ConsumerInsightsService

router = APIRouter(prefix="/consumers", tags=["Consumidores & Mercado"])

_insights = ConsumerInsightsService()


@router.get("/insights", response_model=ConsumerInsightsResponse)
async def get_consumer_insights(
    query: str = Query("iogurte probiótico", description="Produto/alimento para buscar avaliações"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Consulta sinais reais de preferência dos consumidores (Amazon Reviews 2023
    via Hugging Face API) + benchmarks da literatura brasileira.
    """
    return await _insights.get_insights_for_preferences([query], limit=limit)


@router.get("/synthetic-test")
async def generate_synthetic_test_consumers(
    qty: int = Query(5, ge=1, le=50, description="Quantidade de consumidores fictícios para testes"),
):
    """
    Gera consumidores sintéticos via Faker (pt_BR) EXCLUSIVAMENTE para testes
    de integração e validação de endpoints. Não representa preferências reais.
    """
    return {
        "warning": "Dados sintéticos gerados via Faker apenas para testes de API.",
        "count": qty,
        "consumers": _insights.generate_synthetic_consumers_for_testing(qty),
    }
