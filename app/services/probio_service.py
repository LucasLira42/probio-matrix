"""
Serviço de dados probióticos curados — inspirado no Probio-Ichnos.

Como o Probio-Ichnos (https://probio-ichnos.streamlit.app/) não expõe API
pública, este serviço mantém uma base de dados curada localmente com
informações científicas sobre cepas probióticas, complementando os dados
brutos do BacDive com:
  - Benefícios de saúde comprovados
  - Mecanismos de ação
  - Aplicações em alimentos
  - Nível de evidência clínica
  - Status regulatório (QPS/GRAS)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.models import (
    GrowthConditions,
    HealthGoal,
    ProbioticStrain,
    SafetyStatus,
    TaxonomyInfo,
)

logger = logging.getLogger(__name__)

# Caminho dos dados curados
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STRAINS_FILE = DATA_DIR / "probiotic_strains.json"

# Mapeamento de benefícios → HealthGoal
BENEFIT_GOAL_MAP: dict[str, list[HealthGoal]] = {
    "diarr": [HealthGoal.DIGESTIVE],
    "intestin": [HealthGoal.DIGESTIVE],
    "constipa": [HealthGoal.DIGESTIVE],
    "digest": [HealthGoal.DIGESTIVE],
    "SII": [HealthGoal.DIGESTIVE],
    "trânsito": [HealthGoal.DIGESTIVE],
    "flatulência": [HealthGoal.DIGESTIVE],
    "inchaço": [HealthGoal.DIGESTIVE],
    "imun": [HealthGoal.IMMUNITY],
    "NK": [HealthGoal.IMMUNITY],
    "IgA": [HealthGoal.IMMUNITY],
    "infecç": [HealthGoal.IMMUNITY],
    "respirat": [HealthGoal.IMMUNITY],
    "alergia": [HealthGoal.ALLERGY],
    "alérgic": [HealthGoal.ALLERGY],
    "dermatite": [HealthGoal.ALLERGY, HealthGoal.SKIN],
    "atópic": [HealthGoal.ALLERGY, HealthGoal.SKIN],
    "pele": [HealthGoal.SKIN],
    "ansiedade": [HealthGoal.MENTAL],
    "estresse": [HealthGoal.MENTAL],
    "sono": [HealthGoal.MENTAL],
    "cognitiv": [HealthGoal.MENTAL],
    "cortisol": [HealthGoal.MENTAL],
    "GABA": [HealthGoal.MENTAL],
    "colesterol": [HealthGoal.CHOLESTEROL],
    "lipídic": [HealthGoal.CHOLESTEROL],
    "LDL": [HealthGoal.CHOLESTEROL],
    "cardiovascular": [HealthGoal.CHOLESTEROL],
    "peso": [HealthGoal.WEIGHT],
    "obesidade": [HealthGoal.WEIGHT],
    "antioxidant": [HealthGoal.GENERAL],
    "vitamina": [HealthGoal.GENERAL],
}


class ProbioService:
    """Serviço de dados probióticos curados (Probio-Ichnos style)."""

    def __init__(self) -> None:
        self._strains: list[ProbioticStrain] = []
        self._loaded = False

    # ── Carregamento ──────────────────────────────────

    def _load_strains(self) -> None:
        """Carrega cepas do arquivo JSON curado."""
        if self._loaded:
            return

        try:
            with open(STRAINS_FILE, "r", encoding="utf-8") as f:
                raw_list = json.load(f)

            for raw in raw_list:
                try:
                    # Parsear taxonomia
                    tax_data = raw.get("taxonomy", {})
                    taxonomy = TaxonomyInfo(
                        domain=tax_data.get("domain", "Bacteria"),
                        phylum=tax_data.get("phylum", ""),
                        genus=tax_data.get("genus", ""),
                        species=tax_data.get("species", ""),
                        strain=tax_data.get("strain", ""),
                        family=tax_data.get("family", ""),
                        order=tax_data.get("order", ""),
                    )

                    # Parsear condições de crescimento
                    gc_data = raw.get("growth_conditions", {})
                    growth = GrowthConditions(**gc_data)

                    # Parsear status de segurança
                    safety_str = raw.get("safety_status", "Unknown")
                    try:
                        safety = SafetyStatus(safety_str)
                    except ValueError:
                        safety = SafetyStatus.UNKNOWN

                    strain = ProbioticStrain(
                        id=raw["id"],
                        name=raw["name"],
                        taxonomy=taxonomy,
                        growth_conditions=growth,
                        health_benefits=raw.get("health_benefits", []),
                        mechanisms_of_action=raw.get("mechanisms_of_action", []),
                        safety_status=safety,
                        recommended_dose_cfu=raw.get("recommended_dose_cfu", "1e9"),
                        food_applications=raw.get("food_applications", []),
                        survival_in_gi_tract=raw.get("survival_in_gi_tract", ""),
                        clinical_evidence_level=raw.get("clinical_evidence_level", "moderate"),
                        sources=raw.get("sources", ["probio-ichnos"]),
                        bacdive_id=raw.get("bacdive_id"),
                    )
                    self._strains.append(strain)
                except Exception as e:
                    logger.warning("Erro ao parsear cepa: %s — %s", raw.get("id", "?"), e)

            self._loaded = True
            logger.info("Carregadas %d cepas probióticas curadas", len(self._strains))

        except FileNotFoundError:
            logger.error("Arquivo de cepas não encontrado: %s", STRAINS_FILE)
        except json.JSONDecodeError as e:
            logger.error("Erro de JSON no arquivo de cepas: %s", e)

    # ── Consultas ─────────────────────────────────────

    def get_all_strains(self) -> list[ProbioticStrain]:
        """Retorna todas as cepas curadas."""
        self._load_strains()
        return self._strains.copy()

    def get_strain_by_id(self, strain_id: str) -> ProbioticStrain | None:
        """Busca cepa por ID."""
        self._load_strains()
        for s in self._strains:
            if s.id == strain_id:
                return s
        return None

    def search_strains(
        self,
        query: str = "",
        genus: str | None = None,
        health_goal: HealthGoal | None = None,
        food_application: str | None = None,
        limit: int = 10,
    ) -> list[ProbioticStrain]:
        """
        Busca cepas com filtros combinados.

        Args:
            query: Texto livre (busca em nome, benefícios, mecanismos)
            genus: Filtro por gênero taxonômico
            health_goal: Filtro por objetivo de saúde
            food_application: Filtro por aplicação alimentar
            limit: Número máximo de resultados
        """
        self._load_strains()
        results = self._strains.copy()

        # Filtro por gênero
        if genus:
            genus_lower = genus.lower()
            results = [
                s for s in results
                if genus_lower in s.taxonomy.genus.lower()
                or genus_lower in s.name.lower()
            ]

        # Filtro por objetivo de saúde
        if health_goal:
            results = [
                s for s in results
                if self._strain_matches_goal(s, health_goal)
            ]

        # Filtro por aplicação alimentar
        if food_application:
            app_lower = food_application.lower()
            results = [
                s for s in results
                if any(app_lower in a.lower() for a in s.food_applications)
            ]

        # Filtro por texto livre
        if query:
            query_lower = query.lower()
            scored = []
            for s in results:
                score = self._text_match_score(s, query_lower)
                if score > 0:
                    scored.append((score, s))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [s for _, s in scored]

        return results[:limit]

    def get_strains_for_health_goal(
        self, goal: HealthGoal, limit: int = 5
    ) -> list[ProbioticStrain]:
        """Retorna cepas recomendadas para um objetivo de saúde."""
        return self.search_strains(health_goal=goal, limit=limit)

    def get_strains_for_food(
        self, food_type: str, limit: int = 5
    ) -> list[ProbioticStrain]:
        """Retorna cepas compatíveis com um tipo de alimento."""
        return self.search_strains(food_application=food_type, limit=limit)

    # ── Helpers ───────────────────────────────────────

    @staticmethod
    def _strain_matches_goal(strain: ProbioticStrain, goal: HealthGoal) -> bool:
        """Verifica se uma cepa é relevante para um objetivo de saúde."""
        benefits_text = " ".join(strain.health_benefits).lower()
        mechanisms_text = " ".join(strain.mechanisms_of_action).lower()
        full_text = benefits_text + " " + mechanisms_text

        for keyword, goals in BENEFIT_GOAL_MAP.items():
            if goal in goals and keyword.lower() in full_text:
                return True
        return False

    @staticmethod
    def _text_match_score(strain: ProbioticStrain, query: str) -> int:
        """Calcula score de relevância para busca textual."""
        score = 0

        # Nome (peso alto)
        if query in strain.name.lower():
            score += 10

        # Gênero/espécie
        if query in strain.taxonomy.genus.lower():
            score += 8
        if query in strain.taxonomy.species.lower():
            score += 7

        # Benefícios
        for b in strain.health_benefits:
            if query in b.lower():
                score += 5

        # Mecanismos
        for m in strain.mechanisms_of_action:
            if query in m.lower():
                score += 3

        # Aplicações
        for a in strain.food_applications:
            if query in a.lower():
                score += 4

        return score
