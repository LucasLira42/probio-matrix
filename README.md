# 🧬 ProbioMatrix

**Sistema Inteligente de Recomendação Probiótica** — integra dados científicos de múltiplos bancos com IA para recomendar as melhores cepas probióticas para as matrizes alimentares preferidas pelo usuário.

---

## 🎯 O que faz?

O ProbioMatrix resolve um problema prático da ciência de alimentos: **quais cepas probióticas funcionam melhor nos alimentos que eu gosto?**

O sistema:
1. **Consulta bancos de dados científicos** (BacDive, Probio-Ichnos) para obter dados sobre cepas probióticas
2. **Captura preferências alimentares** do usuário (incluindo restrições e objetivos de saúde)
3. **Calcula compatibilidade** cepa × matriz alimentar (pH, temperatura, oxigênio, histórico)
4. **Usa IA (Gemini)** para sintetizar todos os dados em recomendações harmônicas e acionáveis

## 📚 Fontes de Dados

| Fonte | URL | Integração |
|-------|-----|-----------|
| **BacDive** | https://bacdive.dsmz.de/ | API REST (metadados bacterianos) |
| **Probio-Ichnos** | https://probio-ichnos.streamlit.app/ | Base curada (dados probióticos) |
| **Amazon Reviews 2023** | Hugging Face (`McAuley-Lab/Amazon-Reviews-2023`) | API REST pública (sinais reais de sabor, textura e sinérese) |
| **NotCo** | https://www.notco.ai/ | Conceitual (mapeamento plant-based / APLV-safe) |
| **Benchmark Tastewise & Gastrograph AI** | Estudos BR (Moratoya 2013; Buehrmann & Werlang 2016; Vasconcelos 2013) | Vetor sensorial 0–10, sinérese e conformidade ANVISA |
| **Faker (`pt_BR`)** | Biblioteca Python | Gerador sintético exclusivo para testes (`/api/consumers/synthetic-test`) |
| **Gemini AI** | Google AI | Síntese de recomendações |

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────────┐
│              Streamlit (Frontend)              │
│   Preferências │ Busca │ Explorar │ Sobre      │
└───────────────────────┬──────────────────────┘
                        │ HTTP
┌───────────────────────▼──────────────────────┐
│              FastAPI (Backend)                 │
│                                               │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │  /api/search │  │ /api/recommendations │   │
│  └──────┬──────┘  └──────────┬───────────┘   │
│         │                    │                │
│  ┌──────▼────────────────────▼───────────┐   │
│  │          Services Layer                │   │
│  │                                        │   │
│  │  ┌────────────┐  ┌────────────────┐   │   │
│  │  │ BacDive    │  │ Probio-Ichnos  │   │   │
│  │  │ Service    │  │ Service        │   │   │
│  │  │ (API REST) │  │ (Base Curada)  │   │   │
│  │  └────────────┘  └────────────────┘   │   │
│  │                                        │   │
│  │  ┌────────────┐  ┌────────────────┐   │   │
│  │  │ FoodMatrix │  │ AI Synthesizer │   │   │
│  │  │ Service    │  │ (Gemini)       │   │   │
│  │  └────────────┘  └────────────────┘   │   │
│  └────────────────────────────────────────┘   │
└───────────────────────────────────────────────┘
```

## 🚀 Como Executar

### 1. Pré-requisitos

- Python 3.11+
- Chave da API Gemini ([obter aqui](https://aistudio.google.com/apikey))
- Conta BacDive (opcional, [registrar aqui](https://bacdive.dsmz.de/api/bacdive/))

### 2. Instalação

```bash
# Clonar/navegar para o diretório
cd probio-matrix

# Criar ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configuração

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com suas chaves
# GEMINI_API_KEY=sua-chave-aqui
# BACDIVE_EMAIL=seu-email (opcional)
# BACDIVE_PASSWORD=sua-senha (opcional)
```

### 4. Executar

```bash
# Terminal 1 — Backend (FastAPI)
python -m app.main

# Terminal 2 — Frontend (Streamlit)
streamlit run frontend/streamlit_app.py
```

Acesse:
- **Frontend Streamlit**: http://localhost:8501
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## 📡 Endpoints da API

### Busca

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/search/strains` | Busca cepas por texto, gênero, objetivo de saúde |
| `GET` | `/api/search/strains` | Lista cepas com filtros |
| `GET` | `/api/search/strains/{id}` | Detalhes de uma cepa |
| `GET` | `/api/search/foods` | Lista matrizes alimentares |
| `GET` | `/api/search/foods/{id}` | Detalhes de uma matriz |

### Consumidores & Testes

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/consumers/insights` | Sinais reais de consumidores (Amazon Reviews 2023 + benchmarks BR) |
| `GET` | `/api/consumers/synthetic-test` | Gera consumidores sintéticos via Faker exclusivamente para testes |

### Recomendações

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/recommendations` | Gera recomendações personalizadas com IA |

#### Exemplo de requisição:

```json
POST /api/recommendations
{
  "preferred_foods": ["iogurte", "kombuchá", "chocolate"],
  "dietary_restrictions": ["lactose_free"],
  "health_goals": ["digestive_health", "immune_support"],
  "allergens_to_avoid": [],
  "prefer_plant_based": true,
  "max_results": 5
}
```

## 🦠 Cepas na Base Curada

| Cepa | Status | Evidência | Destaques |
|------|--------|-----------|-----------|
| *L. rhamnosus* GG | QPS | Forte | A mais estudada; diarreia, imunidade |
| *L. acidophilus* La-5 | QPS | Forte | Digestão de lactose, colesterol |
| *L. plantarum* 299v | QPS | Forte | SII, absorção de ferro |
| *B. longum* BB536 | GRAS | Forte | Alergias, constipação, idosos |
| *B. lactis* HN019 | GRAS | Forte | Trânsito intestinal, imunidade |
| *S. boulardii* CNCM I-745 | GRAS | Forte | C. difficile, diarreia do viajante |
| *L. reuteri* DSM 17938 | QPS | Forte | Cólicas infantis, saúde oral |
| *L. casei* Shirota | QPS | Forte | Eixo intestino-cérebro, NK cells |
| *B. coagulans* GBI-30 | GRAS | Moderada | Esporos termorresistentes! |
| *L. helveticus* R0052 | QPS | Moderada | Ansiedade, sono, anti-hipertensivo |
| *B. breve* M-16V | QPS | Forte | Neonatos, alergias alimentares |
| *L. fermentum* ME-3 | QPS | Moderada | Antioxidante, glutationa |
| *S. thermophilus* | QPS | Moderada | Digestão de lactose, starter |

## 🍽️ Matrizes Alimentares

17 matrizes incluindo: iogurte (lácteo e vegetal), kefir (lácteo e de água), kombuchá, queijo, leites vegetais (soja, aveia), suco de frutas, chocolate (convencional e vegano), vegetais fermentados, smoothie, sorvete, pão de fermentação natural, barras de proteína e cápsulas.

## 🔧 Estrutura do Projeto

```
probio-matrix/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuração (.env)
│   ├── models.py              # Modelos Pydantic
│   ├── main.py                # FastAPI app
│   ├── data/
│   │   ├── probiotic_strains.json  # 13 cepas curadas
│   │   └── food_matrices.json      # 17 matrizes alimentares
│   ├── services/
│   │   ├── bacdive_service.py      # Integração BacDive API
│   │   ├── probio_service.py       # Dados probióticos curados
│   │   ├── food_matrix.py          # Matrizes + compatibilidade
│   │   └── ai_synthesizer.py       # Síntese Gemini AI
│   └── routers/
│       ├── search.py               # Endpoints de busca
│       └── recommendations.py      # Endpoint de recomendações
├── frontend/
│   └── streamlit_app.py           # Interface Streamlit
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Algoritmo de Compatibilidade

O score de compatibilidade (0-100%) considera 5 fatores:

| Fator | Peso | O que avalia |
|-------|------|-------------|
| pH | 30% | pH ótimo da cepa está na faixa da matriz? |
| Temperatura | 25% | Cepa sobrevive ao processamento térmico? |
| Oxigênio | 15% | Requisito de O₂ compatível com o produto? |
| Gênero compatível | 20% | Gênero é listado como compatível com a matriz? |
| Aplicação documentada | 10% | Já existe literatura sobre esta combinação? |

## 📄 Licença

MIT

---

*Desenvolvido com 🧬 — Dados de BacDive (DSMZ), Probio-Ichnos, literatura científica. IA por Google Gemini.*
