"""
Sintetizador de IA — usa Gemini para gerar recomendações harmônicas e coesas
combinando dados de múltiplas fontes (BacDive, Probio-Ichnos, Amazon Reviews 2023,
matrizes sensoriais e estudos brasileiros) com as preferências do usuário.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import google.generativeai as genai

from app.config import get_settings
from app.models import (
    CompatibilityDetail,
    ConsumerReviewInsight,
    FoodMatrix,
    ProbioticStrain,
    Recommendation,
    RecommendationResponse,
    UserPreferences,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
Você é o ProbioMatrix AI — um cientista de alimentos especializado em \
probióticos, análise sensorial e formulação de sobremesas lácteas funcionais \
e matrizes plant-based. Sua missão é sintetizar dados científicos de múltiplas \
fontes (BacDive, Probio-Ichnos, Amazon Reviews 2023 e literatura nacional) e \
gerar recomendações personalizadas, harmônicas e baseadas em evidências.

## Suas Diretrizes

1. **Base científica**: Fundamente cada recomendação em dados reais das cepas \
   (mecanismos de ação, pH, temperatura, sobrevivência GI) e das matrizes.

2. **Segurança & Restrições**: Respeite rigorosamente APLV (alergia à proteína \
   do leite), intolerância à lactose, restrição de açúcar e imunossupressão. \
   Sempre cite status regulatório (QPS/GRAS) e conformidade de dose (ANVISA >= 10^8 UFC/porção).

3. **Alinhamento Sensorial (Gastrograph AI + Estudos BR)**: Conecte a doçura, \
   acidez láctica, cremosidade, textura e controle de sinérese (separação de soro) \
   às preferências do consumidor e aos sinais reais de avaliações (Amazon Reviews).

4. **Praticidade Tecnológica**: Explique como incorporar a cepa sem morte \
   térmica (ex: resfriar pasta base a 10°C antes de inocular, uso de caldas \
   prebióticas como yacon/inulina para efeito simbiótico).

5. **Linguagem clara e estruturada**: Português claro, direto, com seções \
   organizadas: Resumo Personalizado, Top Recomendações, Dicas de Formulação \
   e Considerações de Segurança.
"""


class AISynthesizer:
    """Usa Gemini para sintetizar dados probióticos, sensoriais e de mercado."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        self.temperature = settings.ai_temperature
        self.max_tokens = settings.ai_max_tokens
        self._configured = False

    def _configure(self) -> None:
        if not self._configured and self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True

    def _build_context(
        self,
        preferences: UserPreferences,
        candidates: list[tuple[ProbioticStrain, FoodMatrix, float, CompatibilityDetail]],
        consumer_insights: list[ConsumerReviewInsight] | None = None,
    ) -> str:
        """Monta o contexto completo para o prompt do Gemini."""
        sections = []

        # 1. Perfil do usuário (4 grupos)
        sp = preferences.sensory_preferences
        sections.append("## 👤 Perfil do Consumidor")
        sections.append(f"- **Alimentos/sobremesas preferidos**: {', '.join(preferences.preferred_foods)}")
        if preferences.dietary_restrictions:
            sections.append(f"- **Restrições**: {', '.join(r.value for r in preferences.dietary_restrictions)}")
        sections.append(f"- **APLV (alergia proteína do leite)**: {'SIM (bloqueio rígido)' if preferences.has_aplv else 'Não'}")
        sections.append(f"- **Imunocomprometido**: {'SIM (cautela médica obrigatória)' if preferences.is_immunocompromised else 'Não'}")
        sections.append(f"- **Objetivos de saúde**: {', '.join(g.value for g in preferences.health_goals)}")
        sections.append(
            f"- **Perfil Sensorial**: doçura desejada {sp.desired_sweetness}/10, "
            f"tolerância à acidez {sp.acidity_tolerance}/10, "
            f"textura favorita: {sp.preferred_texture.value}, "
            f"hábito frequente de fermentados: {'Sim' if sp.fermented_habit_high else 'Não'}"
        )

        # 2. Insights de Consumidores (Amazon Reviews 2023 + Estudos)
        if consumer_insights:
            sections.append("\n## 💬 Sinais Reais de Consumidores (Amazon Reviews 2023)")
            for ins in consumer_insights[:3]:
                sections.append(
                    f"- [{ins.product_category} | nota {ins.rating}] {ins.title}: "
                    f"\"{ins.text[:180]}...\" (sinais: {', '.join(ins.sensory_signals)})"
                )

        # 3. Candidatos ranqueados
        sections.append("\n## 🔬 Candidatos (Cepa + Matriz) Ranqueados")
        for i, (strain, matrix, score, detail) in enumerate(candidates, 1):
            msp = matrix.sensory_profile
            sections.append(f"\n### Candidato #{i} — Score Global: {score:.1%}")
            sections.append(f"**Cepa**: {strain.name} ({strain.safety_status.value}, evidência {strain.clinical_evidence_level}, dose {strain.recommended_dose_cfu} UFC)")
            sections.append(f"- Benefícios: {'; '.join(strain.health_benefits[:4])}")
            sections.append(f"- Mecanismos: {'; '.join(strain.mechanisms_of_action[:3])}")
            sections.append(f"- Sobrevivência GI: {strain.survival_in_gi_tract}")
            sections.append(
                f"**Matriz**: {matrix.name} (pH {matrix.properties.ph_range[0]}-{matrix.properties.ph_range[1]}, "
                f"inoculação: {matrix.properties.inoculation_temperature_c or matrix.properties.processing_temperature_max}°C, "
                f"prebióticos: {', '.join(matrix.properties.prebiotic_fibers) or 'nenhum'})"
            )
            sections.append(
                f"- Mapa Sensorial: doçura {msp.sweetness}, acidez {msp.acidity}, "
                f"cremosidade {msp.creaminess}, firmeza {msp.firmness}, "
                f"aeração {msp.aeration}, controle sinérese {msp.syneresis_control}"
            )
            sections.append(f"- Métodos: {'; '.join(matrix.incorporation_methods)}")
            sections.append(f"- Compatibilidade: {detail.notes}")

        return "\n".join(sections)

    async def synthesize(
        self,
        preferences: UserPreferences,
        candidates: list[tuple[ProbioticStrain, FoodMatrix, float, CompatibilityDetail]],
        consumer_insights: list[ConsumerReviewInsight] | None = None,
    ) -> str:
        """Gera síntese harmônica via Gemini combinando todas as fontes."""
        self._configure()
        context = self._build_context(preferences, candidates, consumer_insights)

        user_prompt = f"""\
Com base nos dados científicos, sensoriais e avaliações reais de consumidores abaixo, \
gere uma recomendação personalizada, harmônica e coesa para o usuário. \
Foque nos {preferences.max_results} melhores candidatos, explicando o encaixe \
microbiológico (BacDive + Probio-Ichnos), o encaixe sensorial (doçura, acidez, \
textura, controle de sinérese) e os cuidados tecnológicos de incorporação.

{context}
"""

        if not self.api_key:
            logger.warning("Gemini API key não configurada — gerando síntese local")
            return self._fallback_synthesis(preferences, candidates)

        try:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=SYSTEM_PROMPT,
            )
            response = model.generate_content(
                user_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
            )
            if response and response.text:
                return response.text
            return self._fallback_synthesis(preferences, candidates)
        except Exception as e:
            logger.error("Erro na API Gemini: %s — usando fallback", e)
            return self._fallback_synthesis(preferences, candidates)

    def _fallback_synthesis(
        self,
        preferences: UserPreferences,
        candidates: list[tuple[ProbioticStrain, FoodMatrix, float, CompatibilityDetail]],
    ) -> str:
        """Gera síntese local estruturada quando o Gemini não está disponível."""
        parts = ["# 🧬 Recomendações ProbioMatrix\n"]
        parts.append(
            f"Com base nas suas preferências por **{', '.join(preferences.preferred_foods)}**, "
            f"perfil sensorial (doçura {preferences.sensory_preferences.desired_sweetness}/10, "
            f"tolerância à acidez {preferences.sensory_preferences.acidity_tolerance}/10) e objetivos de "
            f"**{', '.join(g.value.replace('_', ' ') for g in preferences.health_goals)}**, "
            f"avaliamos {len(candidates)} combinações cepa × matriz.\n"
        )

        for i, (strain, matrix, score, detail) in enumerate(
            candidates[: preferences.max_results], 1
        ):
            parts.append(f"## {i}. {strain.name} → {matrix.name} ({score:.0%} compatível)\n")
            parts.append(f"- **Segurança & Dose**: {strain.safety_status.value} | {strain.recommended_dose_cfu} UFC ({'✅ ANVISA OK' if detail.anvisa_dose_compliant else '⚠️ Verificar dose'})")
            if strain.health_benefits:
                parts.append(f"- **Benefícios**: {'; '.join(strain.health_benefits[:3])}")
            parts.append(f"- **Compatibilidade & Sensorial**: {detail.notes}")
            parts.append(f"- **💡 Formulação**: {'; '.join(matrix.incorporation_methods[:2])}\n")

        parts.append("## ⚠️ Considerações de Segurança\n")
        if preferences.is_immunocompromised:
            parts.append("- **Atenção clínica**: Você indicou condição de imunossupressão — consulte seu médico antes de consumir microrganismos vivos.")
        parts.append("- Viabilidade celular (UFC/porção) depende de cadeia fria e controle de pós-acidificação até o fim da validade.")
        parts.append("\n---\n*Fontes: BacDive (DSMZ), Probio-Ichnos, Amazon Reviews 2023 (McAuley Lab) e literatura científica.*")
        return "\n".join(parts)

    async def generate_full_response(
        self,
        preferences: UserPreferences,
        candidates: list[tuple[ProbioticStrain, FoodMatrix, float, CompatibilityDetail]],
        sources_used: list[str],
        consumer_insights: list[ConsumerReviewInsight] | None = None,
    ) -> RecommendationResponse:
        """Gera a resposta completa com recomendações estruturadas + síntese IA."""
        ai_summary = await self.synthesize(preferences, candidates, consumer_insights)

        recommendations = [
            Recommendation(
                strain=strain,
                food_matrix=matrix,
                compatibility_score=score,
                compatibility_details=detail,
                expected_benefits=strain.health_benefits[:5],
                references=strain.sources,
            )
            for strain, matrix, score, detail in candidates[: preferences.max_results]
        ]

        return RecommendationResponse(
            user_preferences=preferences,
            recommendations=recommendations,
            ai_summary=ai_summary,
            consumer_insights_used=consumer_insights or [],
            data_sources_used=sources_used,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
