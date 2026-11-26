"""Modelos Pydantic para todo o sistema ProbioMatrix."""

from __future__ import annotations

from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════

class SafetyStatus(str, Enum):
    """Status regulatório de segurança da cepa."""
    QPS = "QPS"          # Qualified Presumption of Safety (EFSA)
    GRAS = "GRAS"        # Generally Recognized As Safe (FDA)
    IDA = "IDA"          # Ingestão Diária Aceitável definida
    NOVEL = "Novel Food" # Requer aprovação como novel food
    UNKNOWN = "Unknown"


class DietaryRestriction(str, Enum):
    """Restrições alimentares suportadas."""
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    LACTOSE_FREE = "lactose_free"
    GLUTEN_FREE = "gluten_free"
    SUGAR_FREE = "sugar_free"
    KOSHER = "kosher"
    HALAL = "halal"
    NUT_FREE = "nut_free"
    SOY_FREE = "soy_free"


class HealthGoal(str, Enum):
    """Objetivos de saúde do usuário."""
    DIGESTIVE = "digestive_health"
    IMMUNITY = "immune_support"
    MENTAL = "mental_health"
    SKIN = "skin_health"
    WEIGHT = "weight_management"
    ALLERGY = "allergy_reduction"
    CHOLESTEROL = "cholesterol_reduction"
    GLYCEMIC = "glycemic_control"
    SATIETY = "satiety_protein"
    GENERAL = "general_wellness"


class FoodCategory(str, Enum):
    """Categorias de matrizes alimentares."""
    DAIRY = "dairy"
    DAIRY_DESSERT = "dairy_dessert"
    PLANT_BASED = "plant_based"
    FERMENTED = "fermented"
    BEVERAGE = "beverage"
    CONFECTIONERY = "confectionery"
    BAKERY = "bakery"
    SUPPLEMENT = "supplement"
    FROZEN = "frozen"


class PreferredTexture(str, Enum):
    """Texturas preferidas para sobremesas e matrizes."""
    CREAMY = "creamy"       # Cremosa / ganache
    AERATED = "aerated"     # Aerada / mousse
    FIRM = "firm"           # Firme / flan
    LAYERED = "layered"     # Multicamadas (frutas + crocante)
    FLUID = "fluid"         # Fluida / bebida
    ANY = "any"


# ═══════════════════════════════════════════════════════
#  Taxonomia e Condições de Crescimento
# ═══════════════════════════════════════════════════════

class TaxonomyInfo(BaseModel):
    """Classificação taxonômica da cepa."""
    domain: str = "Bacteria"
    phylum: str = ""
    class_name: str = Field("", alias="class")
    order: str = ""
    family: str = ""
    genus: str
    species: str
    strain: str = ""

    model_config = {"populate_by_name": True}


class GrowthConditions(BaseModel):
    """Condições ótimas de crescimento."""
    temperature_min: float = Field(0, description="°C mínima")
    temperature_opt: float = Field(37, description="°C ótima")
    temperature_max: float = Field(50, description="°C máxima")
    ph_min: float = Field(3.0, description="pH mínimo")
    ph_opt: float = Field(6.5, description="pH ótimo")
    ph_max: float = Field(8.0, description="pH máximo")
    oxygen_requirement: str = Field(
        "facultative anaerobe",
        description="Requisito de oxigênio",
    )
    nacl_tolerance_percent: float = Field(
        2.0, description="Tolerância a NaCl (%)"
    )


# ═══════════════════════════════════════════════════════
#  Cepa Probiótica
# ═══════════════════════════════════════════════════════

class ProbioticStrain(BaseModel):
    """Dados completos de uma cepa probiótica."""
    id: str
    name: str = Field(..., description="Nome completo (ex: Lactobacillus rhamnosus GG)")
    taxonomy: TaxonomyInfo
    growth_conditions: GrowthConditions = GrowthConditions()
    health_benefits: list[str] = []
    mechanisms_of_action: list[str] = []
    safety_status: SafetyStatus = SafetyStatus.UNKNOWN
    recommended_dose_cfu: str = Field("1e9", description="Dose recomendada (UFC)")
    food_applications: list[str] = []
    survival_in_gi_tract: str = ""
    clinical_evidence_level: str = Field(
        "moderate", description="Nível de evidência (strong/moderate/limited/emerging)"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Fontes de dados (bacdive, probio-ichnos, literature)",
    )
    bacdive_id: int | None = None


# ═══════════════════════════════════════════════════════
#  Mapa Sensorial & Propriedades da Matriz Alimentar
# ═══════════════════════════════════════════════════════

class SensoryProfile(BaseModel):
    """
    Vetor sensorial comparável (escala 0 a 10), inspirado no Gastrograph AI
    e adaptado para sobremesas lácteas funcionais (Vasconcelos et al., 2013).
    """
    sweetness: float = Field(5.0, ge=0, le=10, description="Doçura (0-10)")
    acidity: float = Field(4.0, ge=0, le=10, description="Acidez láctica (0-10)")
    creaminess: float = Field(6.0, ge=0, le=10, description="Cremosidade na boca (0-10)")
    firmness: float = Field(5.0, ge=0, le=10, description="Firmeza à colher (0-10)")
    aeration: float = Field(3.0, ge=0, le=10, description="Leveza / aeração (0-10)")
    fermented_note: float = Field(4.0, ge=0, le=10, description="Nota fermentada (0-10)")
    syneresis_control: float = Field(
        7.0, ge=0, le=10, description="Estabilidade / ausência de separação de soro (0-10)"
    )


class MatrixProperties(BaseModel):
    """Propriedades físico-químicas e tecnológicas da matriz alimentar."""
    ph_range: tuple[float, float] = (4.0, 7.0)
    water_activity: float = Field(0.98, ge=0, le=1)
    processing_temperature_max: float = Field(
        72, description="Temperatura máxima de processamento (°C)"
    )
    inoculation_temperature_c: float | None = Field(
        None, description="Temperatura recomendada de inoculação probiótica (°C)"
    )
    shelf_life_days: int = 30
    requires_refrigeration: bool = True
    fermentation_involved: bool = False
    fat_content_percent: float = 3.0
    sugar_content_percent: float = 5.0
    contains_dairy_protein: bool = False
    contains_lactose: bool = False
    prebiotic_fibers: list[str] = Field(
        default_factory=list,
        description="Fibras prebióticas presentes (ex: inulina, FOS, yacon, beta-glucana)",
    )


class FoodMatrix(BaseModel):
    """Matriz alimentar onde probióticos podem ser incorporados."""
    id: str
    name: str
    category: FoodCategory
    description: str = ""
    properties: MatrixProperties = MatrixProperties()
    sensory_profile: SensoryProfile = SensoryProfile()
    compatible_genera: list[str] = Field(
        default_factory=list,
        description="Gêneros bacterianos compatíveis",
    )
    incorporation_methods: list[str] = []
    dietary_tags: list[DietaryRestriction] = []
    is_plant_based: bool = False
    base_ingredients: list[str] = []


# ═══════════════════════════════════════════════════════
#  Preferências do Usuário (4 Grupos — Benchmark Doc 2)
# ═══════════════════════════════════════════════════════

class SensoryPreferences(BaseModel):
    """Preferências sensoriais do consumidor (escala 0 a 10)."""
    desired_sweetness: float = Field(6.0, ge=0, le=10, description="Doçura desejada (0-10)")
    acidity_tolerance: float = Field(5.0, ge=0, le=10, description="Tolerância à acidez (0-10)")
    preferred_texture: PreferredTexture = PreferredTexture.ANY
    fermented_habit_high: bool = Field(
        False, description="Consome iogurte natural/kefir com frequência?"
    )


class UserPreferences(BaseModel):
    """Preferências, segurança e perfil sensorial do usuário."""
    preferred_foods: list[str] = Field(
        ..., min_length=1,
        description="Alimentos/sobremesas/matrizes preferidos",
    )
    dietary_restrictions: list[DietaryRestriction] = []
    has_aplv: bool = Field(
        False, description="Alergia à proteína do leite de vaca (bloqueio rígido de lácteos)"
    )
    is_immunocompromised: bool = Field(
        False, description="Condição clínica que exige cautela com probióticos vivos"
    )
    health_goals: list[HealthGoal] = [HealthGoal.GENERAL]
    sensory_preferences: SensoryPreferences = SensoryPreferences()
    allergens_to_avoid: list[str] = []
    prefer_plant_based: bool = False
    max_results: int = Field(5, ge=1, le=20)


# ═══════════════════════════════════════════════════════
#  Insights de Consumidores (Amazon Reviews 2023 + Estudos)
# ═══════════════════════════════════════════════════════

class ConsumerReviewInsight(BaseModel):
    """Insight extraído de avaliações reais de consumidores ou literatura."""
    source: str
    product_category: str
    rating: float | None = None
    title: str = ""
    text: str
    sensory_signals: list[str] = Field(
        default_factory=list,
        description="Sinais sensoriais detectados (sabor, textura, acidez, sinérese, preço)",
    )


class ConsumerInsightsResponse(BaseModel):
    """Resposta agregada de insights de consumidores."""
    query: str
    insights: list[ConsumerReviewInsight]
    market_benchmarks: list[str] = []
    sources_used: list[str] = []


# ═══════════════════════════════════════════════════════
#  Recomendação
# ═══════════════════════════════════════════════════════

class CompatibilityDetail(BaseModel):
    """Detalhes de compatibilidade cepa ↔ matriz ↔ consumidor."""
    ph_compatible: bool = True
    temperature_compatible: bool = True
    oxygen_compatible: bool = True
    sensory_match_score: float = Field(1.0, ge=0, le=1)
    anvisa_dose_compliant: bool = True
    survival_estimate: str = "good"
    notes: str = ""


class Recommendation(BaseModel):
    """Uma recomendação completa cepa + matriz."""
    strain: ProbioticStrain
    food_matrix: FoodMatrix
    compatibility_score: float = Field(
        ..., ge=0, le=1, description="Score 0-1 de compatibilidade"
    )
    compatibility_details: CompatibilityDetail = CompatibilityDetail()
    scientific_rationale: str = ""
    formulation_tips: str = ""
    expected_benefits: list[str] = []
    references: list[str] = []


class RecommendationResponse(BaseModel):
    """Resposta completa com recomendações sintetizadas pela IA."""
    user_preferences: UserPreferences
    recommendations: list[Recommendation]
    ai_summary: str = Field(
        ..., description="Síntese harmônica gerada pela IA"
    )
    consumer_insights_used: list[ConsumerReviewInsight] = []
    data_sources_used: list[str] = []
    generated_at: str = ""


# ═══════════════════════════════════════════════════════
#  Busca
# ═══════════════════════════════════════════════════════

class StrainSearchRequest(BaseModel):
    """Requisição de busca por cepas."""
    query: str = Field(..., min_length=2)
    genus: str | None = None
    health_benefit: HealthGoal | None = None
    food_application: str | None = None
    limit: int = Field(10, ge=1, le=50)


class StrainSearchResponse(BaseModel):
    """Resultado de busca por cepas."""
    results: list[ProbioticStrain]
    total: int
    sources_queried: list[str]
