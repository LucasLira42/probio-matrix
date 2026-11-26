"""
🧬 ProbioMatrix — Frontend Streamlit

Interface interativa para o sistema de recomendação probiótica e sensorial.
Conecta-se à API FastAPI para buscar dados (BacDive, Probio-Ichnos,
Amazon Reviews 2023) e gerar recomendações personalizadas via Gemini AI.

Uso:
    streamlit run frontend/streamlit_app.py
"""

import requests
import streamlit as st

st.set_page_config(
    page_title="🧬 ProbioMatrix",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = st.sidebar.text_input("🔗 API URL", value="http://localhost:8000")

st.title("🧬 ProbioMatrix")
st.markdown(
    "**Sistema Inteligente de Recomendação Probiótica & Sensorial** — integrando "
    "dados científicos (BacDive, Probio-Ichnos), preferências reais de consumidores "
    "(Amazon Reviews 2023 + estudos BR) e IA (Gemini) para recomendar cepas nas "
    "matrizes alimentares e sobremesas lácteas funcionais ideais para você."
)
st.divider()

# ═══════════════════════════════════════════════════════
#  Sidebar — 4 Grupos de Variáveis do Consumidor
# ═══════════════════════════════════════════════════════

st.sidebar.header("👤 Perfil do Consumidor")

# 1. Alimentos / Sobremesas favoritos
st.sidebar.subheader("🍽️ Alimentos & Sobremesas Favoritos")
food_options = [
    "Flan Simbiótico",
    "Sobremesa Láctea em Camadas",
    "Mousse Probiótica",
    "Skyr / Iogurte Grego",
    "Basque Cheesecake",
    "Iogurte",
    "Iogurte Vegetal",
    "Kefir",
    "Kombuchá",
    "Chocolate",
    "Suco de frutas",
    "Leite de aveia",
    "Smoothie",
    "Sorvete",
]
selected_foods = st.sidebar.multiselect(
    "Selecione seus alimentos/sobremesas preferidos:",
    food_options,
    default=["Flan Simbiótico", "Sobremesa Láctea em Camadas", "Iogurte"],
)
custom_food = st.sidebar.text_input("Ou digite outro alimento:")
if custom_food:
    selected_foods.append(custom_food)

# 2. Segurança e Restrições (Filtros obrigatórios)
st.sidebar.subheader("🛡️ Segurança & Restrições")
has_aplv = st.sidebar.checkbox("🥛🚫 APLV (Alergia à Proteína do Leite — bloqueia lácteos)")
is_immunocompromised = st.sidebar.checkbox("⚕️ Imunossupressão (cautela com probióticos vivos)")
prefer_plant = st.sidebar.checkbox("🌱 Preferência plant-based (conceito NotCo)")

restrictions_map = {
    "Vegano": "vegan",
    "Vegetariano": "vegetarian",
    "Sem lactose": "lactose_free",
    "Sem glúten": "gluten_free",
    "Sem açúcar": "sugar_free",
    "Sem nozes": "nut_free",
    "Sem soja": "soy_free",
}
selected_restrictions = st.sidebar.multiselect(
    "Restrições adicionais:",
    list(restrictions_map.keys()),
)

# 3. Preferências Sensoriais (Gastrograph AI style)
st.sidebar.subheader("👅 Preferências Sensoriais (0–10)")
desired_sweetness = st.sidebar.slider("Doçura desejada", 0.0, 10.0, 6.5, 0.5)
acidity_tolerance = st.sidebar.slider("Tolerância à acidez láctica", 0.0, 10.0, 4.5, 0.5)
texture_map = {
    "Qualquer textura": "any",
    "Cremosa / Ganache": "creamy",
    "Aerada / Mousse": "aerated",
    "Firme / Flan": "firm",
    "Multicamadas (frutas + crocante)": "layered",
    "Fluida / Bebida": "fluid",
}
selected_texture = st.sidebar.selectbox("Textura favorita:", list(texture_map.keys()))
fermented_habit = st.sidebar.checkbox("Consumo iogurte natural/kefir com frequência")

# 4. Objetivos de Saúde
st.sidebar.subheader("🎯 Objetivos de Saúde")
goals_map = {
    "🫃 Saúde Digestiva": "digestive_health",
    "🛡️ Imunidade": "immune_support",
    "🧠 Saúde Mental": "mental_health",
    "✨ Saúde da Pele": "skin_health",
    "⚖️ Controle de Peso": "weight_management",
    "🍬 Controle Glicêmico": "glycemic_control",
    "💪 Saciedade / Proteína": "satiety_protein",
    "🤧 Redução de Alergias": "allergy_reduction",
    "❤️ Colesterol": "cholesterol_reduction",
    "💚 Bem-estar Geral": "general_wellness",
}
selected_goals = st.sidebar.multiselect(
    "Selecione objetivos:",
    list(goals_map.keys()),
    default=["🫃 Saúde Digestiva"],
)

max_results = st.sidebar.slider("📊 Número de recomendações", 1, 10, 5)

# ═══════════════════════════════════════════════════════
#  Tabs Principais
# ═══════════════════════════════════════════════════════

tab_rec, tab_consumers, tab_search, tab_explore, tab_about = st.tabs(
    [
        "🎯 Recomendações",
        "💬 Insights de Consumidores",
        "🔍 Buscar Cepas",
        "📋 Explorar Matrizes",
        "ℹ️ Sobre",
    ]
)

# ─── Tab: Recomendações ──────────────────────────────

with tab_rec:
    st.header("🎯 Recomendações Personalizadas")

    if not selected_foods:
        st.info("👈 Selecione seus alimentos favoritos na barra lateral para começar!")
    else:
        st.markdown(
            f"**Alimentos**: {', '.join(selected_foods)} | "
            f"**Textura**: {selected_texture} | "
            f"**Doçura**: {desired_sweetness}/10 | "
            f"**Tolerância Acidez**: {acidity_tolerance}/10"
        )

        if st.button("🧬 Gerar Recomendações", type="primary", use_container_width=True):
            payload = {
                "preferred_foods": selected_foods,
                "dietary_restrictions": [restrictions_map[r] for r in selected_restrictions],
                "has_aplv": has_aplv,
                "is_immunocompromised": is_immunocompromised,
                "health_goals": [goals_map[g] for g in selected_goals] or ["general_wellness"],
                "sensory_preferences": {
                    "desired_sweetness": desired_sweetness,
                    "acidity_tolerance": acidity_tolerance,
                    "preferred_texture": texture_map[selected_texture],
                    "fermented_habit_high": fermented_habit,
                },
                "prefer_plant_based": prefer_plant,
                "max_results": max_results,
            }

            with st.spinner("🔬 Consultando BacDive + Probio-Ichnos + Amazon Reviews 2023 + Gemini AI..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/api/recommendations",
                        json=payload,
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    st.markdown("---")
                    st.markdown("## 🤖 Síntese da IA")
                    st.markdown(data.get("ai_summary", ""))

                    st.markdown("---")
                    st.markdown("## 📊 Recomendações Detalhadas")

                    recs = data.get("recommendations", [])
                    for i, rec in enumerate(recs, 1):
                        strain = rec["strain"]
                        matrix = rec["food_matrix"]
                        score = rec["compatibility_score"]

                        with st.expander(
                            f"**#{i}** {strain['name']} → {matrix['name']}  "
                            f"({'⭐' * max(1, int(score * 5))} {score:.0%})",
                            expanded=(i <= 3),
                        ):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("### 🦠 Cepa Probiótica")
                                st.markdown(f"**{strain['name']}**")
                                st.markdown(f"- 🏷️ Status: `{strain['safety_status']}` | Evidência: `{strain['clinical_evidence_level']}`")
                                st.markdown(f"- 💊 Dose: {strain['recommended_dose_cfu']} UFC")
                                st.markdown(f"- 🫁 Sobrevivência GI: {strain['survival_in_gi_tract']}")
                                st.markdown("**Benefícios:**")
                                for b in strain.get("health_benefits", [])[:4]:
                                    st.markdown(f"  - {b}")

                            with col2:
                                st.markdown("### 🍽️ Matriz & Perfil Sensorial")
                                st.markdown(f"**{matrix['name']}**")
                                props = matrix["properties"]
                                sp = matrix.get("sensory_profile", {})
                                ph = props["ph_range"]
                                st.markdown(f"- 🧪 pH: {ph[0]}–{ph[1]} | Inoculação: {props.get('inoculation_temperature_c') or props['processing_temperature_max']}°C")
                                st.markdown(f"- 👅 Doçura: {sp.get('sweetness', '?')}/10 | Acidez: {sp.get('acidity', '?')}/10 | Cremosidade: {sp.get('creaminess', '?')}/10")
                                if props.get("prebiotic_fibers"):
                                    st.markdown(f"- 🌾 Prebióticos: {', '.join(props['prebiotic_fibers'])}")
                                st.markdown("**Como incorporar:**")
                                for m in matrix.get("incorporation_methods", [])[:2]:
                                    st.markdown(f"  - {m}")

                            detail = rec.get("compatibility_details", {})
                            st.markdown("---")
                            c1, c2, c3, c4, c5 = st.columns(5)
                            c1.metric("pH", "✅" if detail.get("ph_compatible") else "❌")
                            c2.metric("Temp/Inoc.", "✅" if detail.get("temperature_compatible") else "❌")
                            c3.metric("Sensorial", f"{detail.get('sensory_match_score', 1.0):.0%}")
                            c4.metric("Dose ANVISA", "✅" if detail.get("anvisa_dose_compliant") else "⚠️")
                            c5.metric("Sobrevivência", detail.get("survival_estimate", "?"))

                            if detail.get("notes"):
                                st.info(f"📝 {detail['notes']}")

                    insights_used = data.get("consumer_insights_used", [])
                    if insights_used:
                        st.markdown("---")
                        st.markdown("### 💬 Sinais de Consumidores Considerados (Amazon Reviews 2023)")
                        for ins in insights_used:
                            st.markdown(
                                f"- **[{ins.get('rating', '?')}★] {ins.get('title', '')}** — "
                                f"_{ins.get('text', '')[:180]}_ (Sinais: `{', '.join(ins.get('sensory_signals', []))}`)"
                            )

                    st.markdown("---")
                    sources = data.get("data_sources_used", [])
                    st.caption(f"📚 Fontes consultadas: {', '.join(sources)} | Gerado em: {data.get('generated_at', 'N/A')}")

                except requests.ConnectionError:
                    st.error("❌ API não disponível. Inicie o backend: `python -m app.main`")
                except requests.HTTPError as e:
                    st.error(f"❌ Erro da API: {e.response.status_code} — {e.response.text}")
                except Exception as e:
                    st.error(f"❌ Erro inesperado: {e}")

# ─── Tab: Insights de Consumidores ──────────────────

with tab_consumers:
    st.header("💬 Insights de Consumidores (Amazon Reviews 2023 & Estudos BR)")
    st.markdown(
        "Consulta avaliações reais do nicho *Grocery & Gourmet Food* (McAuley-Lab / Hugging Face) "
        "e benchmarks científicos brasileiros sobre sobremesas lácteas funcionais."
    )

    c_query = st.text_input("🔎 Buscar avaliações de consumidores por termo:", value="probiotic yogurt")
    if st.button("Consultar Insights", key="insights_btn"):
        try:
            resp = requests.get(f"{API_URL}/api/consumers/insights", params={"query": c_query, "limit": 5}, timeout=20)
            resp.raise_for_status()
            cdata = resp.json()

            st.subheader("🛒 Avaliações de Consumidores (Amazon Reviews 2023)")
            for ins in cdata.get("insights", []):
                with st.expander(f"⭐ {ins.get('rating', '?')} — {ins.get('title', 'Review')}"):
                    st.write(ins.get("text", ""))
                    st.caption(f"Sinais sensoriais: {', '.join(ins.get('sensory_signals', []))} | Fonte: {ins.get('source')}")

            st.subheader("📚 Benchmarks de Estudos Brasileiros & Mercado")
            for bm in cdata.get("market_benchmarks", []):
                st.markdown(f"- {bm}")
        except requests.ConnectionError:
            st.error("❌ API não disponível.")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

# ─── Tab: Buscar Cepas ──────────────────────────────

with tab_search:
    st.header("🔍 Buscar Cepas Probióticas")
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Buscar por nome, gênero ou benefício:", placeholder="Ex: Lactobacillus, diarreia, imunidade...")
    with col2:
        limit = st.number_input("Resultados", min_value=1, max_value=50, value=10)

    if query and st.button("Buscar", key="search_btn"):
        with st.spinner("Buscando..."):
            try:
                resp = requests.post(
                    f"{API_URL}/api/search/strains",
                    json={"query": query, "limit": limit},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                st.success(f"Encontradas {data.get('total', len(results))} cepas (fontes: {', '.join(data.get('sources_queried', []))})")

                for strain in results:
                    with st.expander(f"🦠 {strain['name']} ({strain['safety_status']})"):
                        st.markdown(f"**Gênero**: {strain['taxonomy']['genus']} | **Espécie**: {strain['taxonomy']['species']}")
                        st.markdown(f"**Benefícios**: {'; '.join(strain.get('health_benefits', [])[:3])}")
                        st.markdown(f"**Aplicações**: {', '.join(strain.get('food_applications', []))}")
                        st.markdown(f"**Sobrevivência GI**: {strain.get('survival_in_gi_tract', 'N/A')}")
                        if strain.get("bacdive_id"):
                            st.markdown(f"[🔗 Ver no BacDive](https://bacdive.dsmz.de/strain/{strain['bacdive_id']})")
            except requests.ConnectionError:
                st.error("❌ API não disponível.")
            except Exception as e:
                st.error(f"❌ Erro: {e}")

# ─── Tab: Explorar Matrizes ─────────────────────────

with tab_explore:
    st.header("📋 Matrizes Alimentares Disponíveis")
    col1, col2 = st.columns(2)
    with col1:
        cat_filter = st.selectbox(
            "Filtrar por categoria:",
            ["Todas", "Sobremesas Lácteas", "Lácteos", "Plant-based", "Fermentados", "Bebidas", "Confeitaria", "Panificação", "Congelados", "Suplementos"],
        )
    with col2:
        plant_filter = st.checkbox("Apenas plant-based", key="plant_explore")

    cat_map = {
        "Todas": None, "Sobremesas Lácteas": "dairy_dessert", "Lácteos": "dairy",
        "Plant-based": "plant_based", "Fermentados": "fermented", "Bebidas": "beverage",
        "Confeitaria": "confectionery", "Panificação": "bakery",
        "Congelados": "frozen", "Suplementos": "supplement",
    }

    if st.button("Carregar Matrizes", key="load_matrices"):
        try:
            params = {"limit": 50}
            if cat_map.get(cat_filter):
                params["category"] = cat_map[cat_filter]
            if plant_filter:
                params["plant_based"] = True

            resp = requests.get(f"{API_URL}/api/search/foods", params=params, timeout=15)
            resp.raise_for_status()
            matrices = resp.json()

            for matrix in matrices:
                emoji = "🌱" if matrix.get("is_plant_based") else "🍮" if matrix["category"] == "dairy_dessert" else "🥛"
                with st.expander(f"{emoji} {matrix['name']} ({matrix['category']})"):
                    st.markdown(f"_{matrix.get('description', '')}_")
                    props = matrix.get("properties", {})
                    sp = matrix.get("sensory_profile", {})
                    c1, c2, c3, c4 = st.columns(4)
                    ph = props.get("ph_range", [0, 0])
                    c1.metric("pH", f"{ph[0]}–{ph[1]}")
                    c2.metric("Doçura", f"{sp.get('sweetness', '?')}/10")
                    c3.metric("Acidez", f"{sp.get('acidity', '?')}/10")
                    c4.metric("Cremosidade", f"{sp.get('creaminess', '?')}/10")

                    st.markdown(f"**Gêneros compatíveis**: {', '.join(matrix.get('compatible_genera', []))}")
                    st.markdown(f"**Ingredientes**: {', '.join(matrix.get('base_ingredients', []))}")
        except requests.ConnectionError:
            st.error("❌ API não disponível.")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

# ─── Tab: Sobre ──────────────────────────────────────

with tab_about:
    st.header("ℹ️ Sobre o ProbioMatrix")
    st.markdown("""
    ### 🧬 O que é?
    O **ProbioMatrix** integra dados científicos microbiológicos, sinais reais de consumidores e modelagem sensorial para recomendar cepas probióticas em matrizes alimentares e sobremesas lácteas funcionais.

    ### 📚 Fontes Integradas
    | Fonte | Função |
    |-------|--------|
    | [BacDive](https://bacdive.dsmz.de/) | Metadados bacterianos (taxonomia, pH, temperatura, O₂) |
    | [Probio-Ichnos](https://probio-ichnos.streamlit.app/) | Dados probióticos curados (benefícios clínicos, evidência, QPS/GRAS) |
    | [Amazon Reviews 2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) | Sinais reais de sabor, textura, acidez e sinérese (via Hugging Face API) |
    | [NotCo](https://www.notco.ai/) | Conceito de matrizes plant-based seguras para APLV/lactose |
    | Benchmark Tastewise & Gastrograph AI | Vetor sensorial 0–10 e estudos brasileiros (UFV, Embrapa/UFG, FAI) |
    | Gemini AI | Síntese harmônica e coesa de todas as fontes |
    """)

st.sidebar.divider()
st.sidebar.caption("🧬 ProbioMatrix v1.1 — BacDive · Probio-Ichnos · Amazon Reviews 2023 · Gemini AI")
