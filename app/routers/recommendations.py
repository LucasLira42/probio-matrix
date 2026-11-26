"""
Router de recomendações — endpoint principal que integra todas as fontes
(BacDive, Probio-Ichnos, Amazon Reviews 2023, matrizes sensoriais) e usa IA
para gerar recomendações personalizadas.
"""

from __future__ import annotations

import logging
from itertools import product as cartesian_product

from fastapi import APIRouter

from app.models import (
    CompatibilityDetail,
    FoodMatrix,
    ProbioticStrain,
    RecommendationResponse,
    UserPreferences,
)
from app.services.ai_synthesizer import AISynthesizer
from app.services.bacdive_service import BacDiveService
from app.services.consumer_insights import ConsumerInsightsService
from app.services.food_matrix import FoodMatrixService
from app.services.probio_service import ProbioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recomendações"])

_probio = ProbioService()
_food = FoodMatrixService()
_bacdive = BacDiveService()
_insights = ConsumerInsightsService()
_ai = AISynthesizer()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(preferences: UserPreferences):
    """
    🧬 Endpoint principal — gera recomendações personalizadas de cepas + matrizes.

    Pipeline:
    1. Aplica filtros obrigatórios de segurança (APLV, restrições, plant-based)
    2. Busca cepas probióticas relevantes para os objetivos de saúde
    3. Consulta insights de consumidores (Amazon Reviews 2023 + estudos BR)
    4. Calcula compatibilidade microbiológica + afinidade sensorial (0-10)
    5. Usa Gemini para sintetizar tudo em uma resposta harmônica
    """
    sources_used: list[str] = []

    # ── 1. Encontrar matrizes compatíveis (com bloqueio APLV) ──
    dietary_restrictions = preferences.dietary_restrictions or None

    matched_matrices = _food.find_matrices_for_preferences(
        preferred_foods=preferences.preferred_foods,
        dietary_restrictions=dietary_restrictions,
        prefer_plant_based=preferences.prefer_plant_based,
        has_aplv=preferences.has_aplv,
    )

    if not matched_matrices:
        matched_matrices = _food.search_matrices(
            plant_based_only=preferences.prefer_plant_based,
            dietary_restrictions=dietary_restrictions,
            has_aplv=preferences.has_aplv,
            limit=10,
        )

    if not matched_matrices and not preferences.has_aplv:
        matched_matrices = _food.get_all_matrices()[:5]

    # ── 2. Buscar cepas relevantes ────────────────────
    all_strains: list[ProbioticStrain] = []
    for goal in preferences.health_goals:
        for s in _probio.get_strains_for_health_goal(goal, limit=10):
            if s.id not in {x.id for x in all_strains}:
                all_strains.append(s)
    sources_used.append("probio-ichnos")

    if len(all_strains) < 3:
        for s in _probio.get_all_strains():
            if s.id not in {x.id for x in all_strains}:
                all_strains.append(s)

    try:
        for strain in all_strains[:2]:
            if strain.bacdive_id:
                await _bacdive.get_strain_by_id(strain.bacdive_id)
        sources_used.append("bacdive")
    except Exception as e:
        logger.info("BacDive não disponível: %s", e)

    # ── 3. Insights de consumidores (Amazon Reviews 2023) ──
    consumer_resp = await _insights.get_insights_for_preferences(
        preferences.preferred_foods, limit=3
    )
    sources_used.extend(consumer_resp.sources_used)

    # ── 4. Calcular compatibilidade cepa × matriz × sensorial ──
    candidates: list[tuple[ProbioticStrain, FoodMatrix, float, CompatibilityDetail]] = []
    for strain, matrix in cartesian_product(all_strains, matched_matrices):
        score, detail = _food.calculate_compatibility(
            strain, matrix, preferences.sensory_preferences
        )
        candidates.append((strain, matrix, score, detail))

    candidates.sort(key=lambda x: x[2], reverse=True)
    top_candidates = candidates[: preferences.max_results * 2]

    # ── 5. Síntese com IA ─────────────────────────────
    return await _ai.generate_full_response(
        preferences=preferences,
        candidates=top_candidates,
        sources_used=list(dict.fromkeys(sources_used)),
        consumer_insights=consumer_resp.insights,
    )
