"""
Serviço de Matrizes Alimentares — gerencia dados de alimentos e calcula
compatibilidade microbiológica, sensorial (Gastrograph AI) e regulatória (ANVISA).

Integra conceitos de:
- NotCo (matrizes plant-based)
- Gastrograph AI (vetor sensorial 0-10 e distância matemática)
- Vasconcelos et al. (2013) & Buehrmann & Werlang (2016) (sinérese, inoculação a 10°C, ANVISA)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from app.models import (
    CompatibilityDetail,
    DietaryRestriction,
    FoodCategory,
    FoodMatrix,
    MatrixProperties,
    PreferredTexture,
    ProbioticStrain,
    SensoryPreferences,
    SensoryProfile,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MATRICES_FILE = DATA_DIR / "food_matrices.json"


class FoodMatrixService:
    """Serviço de matrizes alimentares e cálculo de compatibilidade."""

    def __init__(self) -> None:
        self._matrices: list[FoodMatrix] = []
        self._loaded = False

    # ── Carregamento ──────────────────────────────────

    def _load_matrices(self) -> None:
        """Carrega matrizes alimentares do JSON."""
        if self._loaded:
            return

        try:
            with open(MATRICES_FILE, "r", encoding="utf-8") as f:
                raw_list = json.load(f)

            for raw in raw_list:
                try:
                    props_data = raw.get("properties", {})
                    ph = props_data.get("ph_range", [4.0, 7.0])
                    props = MatrixProperties(
                        ph_range=(ph[0], ph[1]) if isinstance(ph, list) else (4.0, 7.0),
                        water_activity=props_data.get("water_activity", 0.98),
                        processing_temperature_max=props_data.get("processing_temperature_max", 72),
                        inoculation_temperature_c=props_data.get("inoculation_temperature_c"),
                        shelf_life_days=props_data.get("shelf_life_days", 30),
                        requires_refrigeration=props_data.get("requires_refrigeration", True),
                        fermentation_involved=props_data.get("fermentation_involved", False),
                        fat_content_percent=props_data.get("fat_content_percent", 3.0),
                        sugar_content_percent=props_data.get("sugar_content_percent", 5.0),
                        contains_dairy_protein=props_data.get("contains_dairy_protein", not raw.get("is_plant_based", False)),
                        contains_lactose=props_data.get("contains_lactose", False),
                        prebiotic_fibers=props_data.get("prebiotic_fibers", []),
                    )

                    sensory_data = raw.get("sensory_profile", {})
                    sensory = SensoryProfile(**sensory_data) if sensory_data else SensoryProfile()

                    tags = []
                    for tag_str in raw.get("dietary_tags", []):
                        try:
                            tags.append(DietaryRestriction(tag_str))
                        except ValueError:
                            pass

                    matrix = FoodMatrix(
                        id=raw["id"],
                        name=raw["name"],
                        category=FoodCategory(raw.get("category", "dairy")),
                        description=raw.get("description", ""),
                        properties=props,
                        sensory_profile=sensory,
                        compatible_genera=raw.get("compatible_genera", []),
                        incorporation_methods=raw.get("incorporation_methods", []),
                        dietary_tags=tags,
                        is_plant_based=raw.get("is_plant_based", False),
                        base_ingredients=raw.get("base_ingredients", []),
                    )
                    self._matrices.append(matrix)
                except Exception as e:
                    logger.warning("Erro ao parsear matriz: %s — %s", raw.get("id", "?"), e)

            self._loaded = True
            logger.info("Carregadas %d matrizes alimentares", len(self._matrices))

        except FileNotFoundError:
            logger.error("Arquivo de matrizes não encontrado: %s", MATRICES_FILE)
        except json.JSONDecodeError as e:
            logger.error("Erro de JSON no arquivo de matrizes: %s", e)

    # ── Consultas ─────────────────────────────────────

    def get_all_matrices(self) -> list[FoodMatrix]:
        """Retorna todas as matrizes."""
        self._load_matrices()
        return self._matrices.copy()

    def get_matrix_by_id(self, matrix_id: str) -> FoodMatrix | None:
        """Busca matriz por ID."""
        self._load_matrices()
        for m in self._matrices:
            if m.id == matrix_id:
                return m
        return None

    def _passes_safety_filters(
        self,
        matrix: FoodMatrix,
        dietary_restrictions: list[DietaryRestriction] | None = None,
        has_aplv: bool = False,
        prefer_plant_based: bool = False,
    ) -> bool:
        """Filtros obrigatórios de segurança e restrição (APLV = bloqueio imediato)."""
        if has_aplv and matrix.properties.contains_dairy_protein:
            return False
        if prefer_plant_based and not matrix.is_plant_based:
            return False
        if dietary_restrictions:
            if not all(r in matrix.dietary_tags for r in dietary_restrictions):
                return False
        return True

    def search_matrices(
        self,
        query: str = "",
        category: FoodCategory | None = None,
        plant_based_only: bool = False,
        dietary_restrictions: list[DietaryRestriction] | None = None,
        has_aplv: bool = False,
        limit: int = 10,
    ) -> list[FoodMatrix]:
        """Busca matrizes alimentares com filtros de segurança e categoria."""
        self._load_matrices()
        results = [
            m for m in self._matrices
            if self._passes_safety_filters(m, dietary_restrictions, has_aplv, plant_based_only)
        ]

        if category:
            results = [m for m in results if m.category == category]

        if query:
            query_lower = query.lower()
            scored = []
            for m in results:
                score = 0
                if query_lower in m.name.lower():
                    score += 10
                if query_lower in m.description.lower():
                    score += 5
                for ing in m.base_ingredients:
                    if query_lower in ing.lower():
                        score += 3
                if score > 0:
                    scored.append((score, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [m for _, m in scored]

        return results[:limit]

    def find_matrices_for_preferences(
        self,
        preferred_foods: list[str],
        dietary_restrictions: list[DietaryRestriction] | None = None,
        prefer_plant_based: bool = False,
        has_aplv: bool = False,
    ) -> list[FoodMatrix]:
        """Encontra matrizes que correspondem às preferências e respeitam filtros de segurança."""
        self._load_matrices()
        matched: list[tuple[int, FoodMatrix]] = []

        for matrix in self._matrices:
            if not self._passes_safety_filters(
                matrix, dietary_restrictions, has_aplv, prefer_plant_based
            ):
                continue

            score = 0
            for pref in preferred_foods:
                pref_lower = pref.lower()
                if pref_lower in matrix.name.lower():
                    score += 10
                for ing in matrix.base_ingredients:
                    if pref_lower in ing.lower():
                        score += 5
                if pref_lower in matrix.description.lower():
                    score += 3
                if pref_lower in matrix.category.value.lower():
                    score += 4

            if score > 0:
                matched.append((score, matrix))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in matched]

    # ── Proximidade Sensorial (Gastrograph AI style) ──

    @staticmethod
    def calculate_sensory_match(
        matrix: FoodMatrix, sensory_prefs: SensoryPreferences | None
    ) -> tuple[float, str]:
        """
        Calcula afinidade sensorial (0-1) via distância matemática entre
        o desejo do consumidor e o vetor sensorial da matriz.
        """
        if sensory_prefs is None:
            return 0.85, "Perfil sensorial padrão"

        sp = matrix.sensory_profile
        # Distância normalizada de doçura e acidez (escala 0-10)
        sweet_diff = abs(sp.sweetness - sensory_prefs.desired_sweetness) / 10.0
        # Penaliza apenas se a acidez da matriz exceder a tolerância do usuário
        acid_excess = max(0.0, sp.acidity - sensory_prefs.acidity_tolerance) / 10.0

        # Ajuste por textura preferida
        texture_bonus = 0.0
        tex = sensory_prefs.preferred_texture
        if tex == PreferredTexture.CREAMY and sp.creaminess >= 7.0:
            texture_bonus = 0.10
        elif tex == PreferredTexture.AERATED and sp.aeration >= 6.0:
            texture_bonus = 0.10
        elif tex == PreferredTexture.FIRM and sp.firmness >= 6.5:
            texture_bonus = 0.10
        elif tex == PreferredTexture.LAYERED and "camadas" in matrix.name.lower():
            texture_bonus = 0.15
        elif tex == PreferredTexture.FLUID and sp.firmness <= 2.5:
            texture_bonus = 0.10

        # Iniciantes costumam rejeitar acidez/fermentação forte (Doc 2, 4.1)
        habit_penalty = 0.0
        if not sensory_prefs.fermented_habit_high and sp.fermented_note >= 7.5:
            habit_penalty = 0.15

        dist = math.sqrt((sweet_diff ** 2 + acid_excess ** 2) / 2.0)
        match = max(0.0, min(1.0, (1.0 - dist) + texture_bonus - habit_penalty))
        note = f"Afinidade sensorial {match:.0%} (doçura {sp.sweetness}/10, acidez {sp.acidity}/10, cremosidade {sp.creaminess}/10)"
        return round(match, 3), note

    # ── Compatibilidade Completa ──────────────────────

    def calculate_compatibility(
        self,
        strain: ProbioticStrain,
        matrix: FoodMatrix,
        sensory_prefs: SensoryPreferences | None = None,
    ) -> tuple[float, CompatibilityDetail]:
        """
        Calcula score de compatibilidade (0-1) combinando:
        1. pH (25%)
        2. Temperatura de processamento / inoculação (20%)
        3. Oxigênio (10%)
        4. Gênero compatível + aplicação documentada (20%)
        5. Afinidade sensorial consumidor ↔ matriz (25%)
        + Verificação regulatória de dose mínima diária (ANVISA: >= 1e8 UFC/porção)
        """
        gc = strain.growth_conditions
        props = matrix.properties
        score = 0.0
        notes_parts: list[str] = []

        # 1. pH (25%)
        ph_min_m, ph_max_m = props.ph_range
        ph_compatible = gc.ph_min <= ph_max_m and gc.ph_max >= ph_min_m
        if ph_compatible:
            if ph_min_m <= gc.ph_opt <= ph_max_m:
                score += 0.25
                notes_parts.append(f"pH ótimo ({gc.ph_opt}) compatível ({ph_min_m}-{ph_max_m})")
            else:
                score += 0.13
                notes_parts.append("pH tolerável na matriz")
        else:
            notes_parts.append(f"⚠ pH ({ph_min_m}-{ph_max_m}) fora da tolerância da cepa ({gc.ph_min}-{gc.ph_max})")

        # 2. Temperatura (20%) — considerando inoculação pós-preparo (ex: 10°C em flan)
        effective_temp = props.inoculation_temperature_c or props.processing_temperature_max
        temp_compatible = effective_temp <= gc.temperature_max
        if temp_compatible:
            score += 0.20
            if props.inoculation_temperature_c:
                notes_parts.append(f"Inoculação a {props.inoculation_temperature_c}°C preserva células vivas")
            else:
                notes_parts.append("Sobrevive ao processamento térmico")
        elif "Bacillus" in strain.taxonomy.genus or "esporo" in strain.survival_in_gi_tract.lower():
            score += 0.18
            temp_compatible = True
            notes_parts.append("Esporos termorresistentes")
        else:
            notes_parts.append(f"⚠ Temp. ({effective_temp}°C) exige adição pós-resfriamento")

        # 3. Oxigênio (10%)
        oxygen_req = gc.oxygen_requirement.lower()
        oxygen_compatible = True
        if "strict anaerobe" in oxygen_req:
            if props.fermentation_involved or props.water_activity < 0.5:
                score += 0.07
                notes_parts.append("Anaeróbio estrito — embalagem com baixa permeabilidade a O₂")
            else:
                score += 0.03
                oxygen_compatible = False
                notes_parts.append("⚠ Anaeróbio estrito — microencapsulação recomendada")
        else:
            score += 0.10

        # 4. Gênero compatível (12%) + Aplicação documentada (8%)
        genus_match = any(
            strain.taxonomy.genus.lower() in g.lower()
            or g.lower() in strain.taxonomy.genus.lower()
            for g in matrix.compatible_genera
        )
        if genus_match:
            score += 0.12

        food_match = any(
            matrix.id.replace("_", " ") in app.lower()
            or app.lower() in matrix.id.replace("_", " ")
            or app.lower() in matrix.name.lower()
            for app in strain.food_applications
        )
        if food_match:
            score += 0.08

        # 5. Afinidade Sensorial (25%)
        sensory_score, sensory_note = self.calculate_sensory_match(matrix, sensory_prefs)
        score += 0.25 * sensory_score
        notes_parts.append(sensory_note)

        # Bônus simbiótico se matriz possui fibras prebióticas (inulina, FOS, yacon)
        if props.prebiotic_fibers:
            notes_parts.append(f"Efeito simbiótico ({', '.join(props.prebiotic_fibers)})")

        # Checagem ANVISA (dose mínima típica 10^8 - 10^9 UFC/porção)
        try:
            dose_val = float(strain.recommended_dose_cfu)
            anvisa_ok = dose_val >= 1e8
        except ValueError:
            anvisa_ok = True

        if score >= 0.75:
            survival = "excellent"
        elif score >= 0.55:
            survival = "good"
        elif score >= 0.35:
            survival = "moderate"
        else:
            survival = "poor"

        detail = CompatibilityDetail(
            ph_compatible=ph_compatible,
            temperature_compatible=temp_compatible,
            oxygen_compatible=oxygen_compatible,
            sensory_match_score=sensory_score,
            anvisa_dose_compliant=anvisa_ok,
            survival_estimate=survival,
            notes=" | ".join(notes_parts),
        )

        return round(min(score, 1.0), 3), detail
