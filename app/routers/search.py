"""Router de busca — endpoints para pesquisar cepas e matrizes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import (
    FoodCategory,
    FoodMatrix,
    HealthGoal,
    ProbioticStrain,
    StrainSearchRequest,
    StrainSearchResponse,
)
from app.services.bacdive_service import BacDiveService
from app.services.probio_service import ProbioService
from app.services.food_matrix import FoodMatrixService

router = APIRouter(prefix="/search", tags=["Busca"])

# Instâncias dos serviços (singleton simples)
_probio = ProbioService()
_food = FoodMatrixService()
_bacdive = BacDiveService()


@router.post("/strains", response_model=StrainSearchResponse)
async def search_strains(request: StrainSearchRequest):
    """
    Busca cepas probióticas nas fontes disponíveis.

    Combina dados do Probio-Ichnos (curados) com BacDive (API).
    """
    # 1. Buscar na base curada (Probio-Ichnos)
    local_results = _probio.search_strains(
        query=request.query,
        genus=request.genus,
        health_goal=request.health_benefit,
        food_application=request.food_application,
        limit=request.limit,
    )
    sources = ["probio-ichnos"]

    # 2. Tentar complementar com BacDive (se configurado)
    bacdive_results: list[ProbioticStrain] = []
    try:
        bacdive_results = await _bacdive.search_probiotic_strains(
            request.query, limit=request.limit
        )
        if bacdive_results:
            sources.append("bacdive")
    except Exception:
        pass  # BacDive pode não estar configurado

    # 3. Merge: priorizar dados curados, complementar com BacDive
    seen_ids = {s.id for s in local_results}
    for bs in bacdive_results:
        if bs.id not in seen_ids:
            local_results.append(bs)
            seen_ids.add(bs.id)

    return StrainSearchResponse(
        results=local_results[: request.limit],
        total=len(local_results),
        sources_queried=sources,
    )


@router.get("/strains/{strain_id}", response_model=ProbioticStrain)
async def get_strain(strain_id: str):
    """Retorna detalhes de uma cepa específica."""
    strain = _probio.get_strain_by_id(strain_id)
    if not strain:
        raise HTTPException(404, f"Cepa '{strain_id}' não encontrada")
    return strain


@router.get("/strains", response_model=list[ProbioticStrain])
async def list_strains(
    health_goal: HealthGoal | None = None,
    food: str | None = None,
    limit: int = Query(10, ge=1, le=50),
):
    """Lista cepas com filtros opcionais."""
    return _probio.search_strains(
        health_goal=health_goal,
        food_application=food,
        limit=limit,
    )


@router.get("/foods", response_model=list[FoodMatrix])
async def list_food_matrices(
    query: str = "",
    category: FoodCategory | None = None,
    plant_based: bool = False,
    limit: int = Query(10, ge=1, le=50),
):
    """Lista matrizes alimentares com filtros."""
    return _food.search_matrices(
        query=query,
        category=category,
        plant_based_only=plant_based,
        limit=limit,
    )


@router.get("/foods/{matrix_id}", response_model=FoodMatrix)
async def get_food_matrix(matrix_id: str):
    """Retorna detalhes de uma matriz alimentar."""
    matrix = _food.get_matrix_by_id(matrix_id)
    if not matrix:
        raise HTTPException(404, f"Matriz '{matrix_id}' não encontrada")
    return matrix
