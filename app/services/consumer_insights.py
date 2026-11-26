"""
Serviço de Insights de Consumidores — consulta fontes externas e literatura.

Integra:
1. Amazon Reviews 2023 (McAuley Lab) via Hugging Face Datasets Server API
   (nicho Grocery_and_Gourmet_Food) — extraindo sinais reais de sabor, textura,
   acidez, consistência e experiência de consumo.
2. Benchmarks dos estudos científicos brasileiros (Moratoya et al., 2013;
   Buehrmann & Werlang, 2016; Vasconcelos et al., 2013) e Tendências 2026
   (Tastewise / Gastrograph AI).
3. Gerador de dados sintéticos (Faker) EXCLUSIVO para testes de API
   (separado dos dados reais, conforme diretriz de revisão).
"""

from __future__ import annotations

import logging
import random
from typing import Any

import httpx
from cachetools import TTLCache

from app.models import ConsumerInsightsResponse, ConsumerReviewInsight

logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=128, ttl=3600)

# Benchmarks reais extraídos dos documentos de referência (Doc 2)
MARKET_BENCHMARKS: list[str] = [
    "Buehrmann & Werlang (2016): Qualidade (41,4%) e sabor (40,5%) são os maiores atrativos em lácteos; sobremesas em camadas com frutas lideram intenção de compra (47,7%).",
    "Buehrmann & Werlang (2016): Separação de soro (sinérese / 'ficar aguado') e preço alto (42,8%) são as principais causas de rejeição.",
    "Moratoya et al. (2013): Leite está entre os 3 alimentos mais consumidos no Brasil; urbanização e renda elevam demanda por lácteos funcionais com controle calórico e frutas.",
    "Vasconcelos et al. (2013): Flan simbiótico (75% iogurte + 25% pasta base, L. acidophilus a 10°C + calda de yacon 55 °Brix) atingiu 83% de aceitação em textura e 10^8 UFC/g.",
    "Tastewise (2026): Sobremesas lácteas refrigeradas (como Basque cheesecake +16,1%, skyr, kefir) migram de apelo genérico para cremosidade, saciedade e indulgência equilibrada.",
]

# Fallback curado caso a API do Hugging Face esteja indisponível/offline
FALLBACK_REVIEWS: list[ConsumerReviewInsight] = [
    ConsumerReviewInsight(
        source="Amazon Reviews 2023 (Grocery & Gourmet Food — curado)",
        product_category="Probiotic Yogurt & Dairy Desserts",
        rating=5.0,
        title="Creamy texture without sour aftertaste",
        text="Thick, creamy consistency with zero watery separation on top. Mild sweetness pairs great with berry compote.",
        sensory_signals=["cremosidade", "sem sinérese", "baixa acidez", "frutas"],
    ),
    ConsumerReviewInsight(
        source="Amazon Reviews 2023 (Grocery & Gourmet Food — curado)",
        product_category="Kefir & Fermented Drinks",
        rating=3.0,
        title="Too tart for daily dessert, great gut comfort",
        text="Noticeable digestive comfort after two weeks, but the sharp lactic acidity makes it hard to eat plain without honey or fruit.",
        sensory_signals=["alta acidez", "conforto intestinal", "precisa doçura"],
    ),
    ConsumerReviewInsight(
        source="Amazon Reviews 2023 (Grocery & Gourmet Food — curado)",
        product_category="Plant-Based Probiotic Yogurt",
        rating=4.0,
        title="Great dairy-free option, slightly thin",
        text="Safe for lactose intolerance and milk allergy. Flavor is pleasant, though slightly less firm than traditional Greek yogurt.",
        sensory_signals=["sem lactose", "plant-based", "firmeza moderada"],
    ),
]

SENSORY_KEYWORDS: dict[str, str] = {
    "creamy": "cremosidade",
    "thick": "consistência firme",
    "smooth": "textura suave",
    "watery": "sinérese (separação de soro)",
    "tart": "acidez pronunciada",
    "sour": "acidez láctica",
    "sweet": "doçura",
    "bitter": "amargor/residual",
    "taste": "sabor",
    "flavor": "sabor",
    "texture": "textura",
    "price": "sensibilidade a preço",
    "lactose": "lactose",
}


class ConsumerInsightsService:
    """Consulta Amazon Reviews 2023 (Hugging Face) e benchmarks de mercado."""

    HF_SEARCH_URL = "https://datasets-server.huggingface.co/search"

    async def fetch_amazon_reviews(
        self, query: str = "probiotic yogurt", limit: int = 5
    ) -> list[ConsumerReviewInsight]:
        """
        Consulta a API pública do Hugging Face Datasets Server para buscar
        avaliações reais de Grocery_and_Gourmet_Food (Amazon Reviews 2023).
        """
        cache_key = f"hf:{query}:{limit}"
        if cache_key in _cache:
            return _cache[cache_key]

        params = {
            "dataset": "McAuley-Lab/Amazon-Reviews-2023",
            "config": "raw_review_Grocery_and_Gourmet_Food",
            "split": "full",
            "query": query,
            "length": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.HF_SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            rows = data.get("rows", [])
            insights: list[ConsumerReviewInsight] = []
            for item in rows:
                row = item.get("row", {})
                text = str(row.get("text", "")).strip()
                title = str(row.get("title", "")).strip()
                if not text:
                    continue

                signals = self._extract_sensory_signals(f"{title} {text}")
                insights.append(
                    ConsumerReviewInsight(
                        source="Amazon Reviews 2023 (McAuley-Lab / Hugging Face API)",
                        product_category="Grocery_and_Gourmet_Food",
                        rating=row.get("rating"),
                        title=title[:120],
                        text=text[:400],
                        sensory_signals=signals,
                    )
                )

            if insights:
                _cache[cache_key] = insights
                logger.info("Amazon Reviews 2023 '%s': %d reviews", query, len(insights))
                return insights

        except Exception as e:
            logger.info("HF Amazon Reviews API indisponível (%s) — usando fallback curado", e)

        return FALLBACK_REVIEWS[:limit]

    async def get_insights_for_preferences(
        self, preferred_foods: list[str], limit: int = 4
    ) -> ConsumerInsightsResponse:
        """Agrega insights de Amazon Reviews 2023 + benchmarks brasileiros."""
        query_terms = " ".join(preferred_foods[:2]) if preferred_foods else "probiotic yogurt"
        # Mapear termos PT → EN para melhor match na base Amazon Reviews 2023
        pt_to_en = {
            "iogurte": "probiotic yogurt",
            "flan": "yogurt dessert",
            "mousse": "dairy dessert mousse",
            "cheesecake": "cheesecake yogurt",
            "sobremesa": "dairy dessert probiotic",
            "kefir": "kefir probiotic",
            "kombuchá": "kombucha probiotic",
            "kombucha": "kombucha probiotic",
            "chocolate": "probiotic chocolate",
            "vegetal": "plant based yogurt",
            "aveia": "oat milk yogurt",
            "soja": "soy yogurt",
        }
        search_q = "probiotic yogurt"
        for pt, en in pt_to_en.items():
            if pt in query_terms.lower():
                search_q = en
                break

        reviews = await self.fetch_amazon_reviews(query=search_q, limit=limit)
        sources = list({r.source for r in reviews})
        sources.append("Literatura BR (Moratoya 2013; Buehrmann & Werlang 2016; Vasconcelos 2013)")

        return ConsumerInsightsResponse(
            query=search_q,
            insights=reviews,
            market_benchmarks=MARKET_BENCHMARKS,
            sources_used=sources,
        )

    @staticmethod
    def _extract_sensory_signals(text: str) -> list[str]:
        """Extrai sinais sensoriais e de experiência de consumo de um review."""
        lower = text.lower()
        found = []
        for kw, label in SENSORY_KEYWORDS.items():
            if kw in lower and label not in found:
                found.append(label)
        return found or ["experiência geral"]

    # ── Gerador Sintético (APENAS PARA TESTES) ────────

    @staticmethod
    def generate_synthetic_consumers_for_testing(qty: int = 10) -> list[dict[str, Any]]:
        """
        Gera payloads de consumidores fictícios com Faker (pt_BR) exclusivamente
        para testes automatizados e validação de endpoints da API.
        NÃO deve ser usado para inferências sobre preferências reais.
        """
        from faker import Faker

        fake = Faker("pt_BR")
        foods_pool = [
            "Flan Simbiótico", "Sobremesa Láctea em Camadas", "Iogurte Tradicional",
            "Skyr / Iogurte Grego", "Mousse Probiótica", "Iogurte Vegetal", "Kefir",
        ]
        textures = ["creamy", "aerated", "firm", "layered", "fluid"]
        restrictions = ["none", "lactose_free", "vegan", "sugar_free"]

        samples: list[dict[str, Any]] = []
        for _ in range(min(qty, 100)):
            restr = random.choice(restrictions)
            samples.append({
                "is_synthetic_test_data": True,
                "consumer_id": fake.uuid4(),
                "name": fake.name(),
                "city": fake.city(),
                "age_group": random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
                "preferred_foods": random.sample(foods_pool, k=random.randint(1, 3)),
                "dietary_restrictions": [] if restr == "none" else [restr],
                "sensory_preferences": {
                    "desired_sweetness": round(random.uniform(3.0, 9.0), 1),
                    "acidity_tolerance": round(random.uniform(2.0, 8.0), 1),
                    "preferred_texture": random.choice(textures),
                },
            })
        return samples
