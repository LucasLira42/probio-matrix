"""Configuração centralizada do ProbioMatrix."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente / .env"""

    # ── API Keys ──────────────────────────────────────
    gemini_api_key: str = ""
    bacdive_email: str = ""
    bacdive_password: str = ""

    # ── Servidor ──────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── IA ────────────────────────────────────────────
    gemini_model: str = "gemini-2.0-flash"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 4096

    # ── Cache ─────────────────────────────────────────
    cache_ttl_seconds: int = 3600  # 1 hora
    cache_max_size: int = 256

    # ── URLs das fontes ──────────────────────────────
    bacdive_api_url: str = "https://bacdive.dsmz.de/api/bacdive"
    probio_ichnos_url: str = "https://probio-ichnos.streamlit.app"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
