"""
Serviço de integração com a API do BacDive (bacdive.dsmz.de).

BacDive (Bacterial Diversity Metadatabase) é o maior banco de dados mundial
de metadados padronizados sobre cepas bacterianas e arqueias.

API Docs: https://bacdive.dsmz.de/api/bacdive/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models import (
    GrowthConditions,
    ProbioticStrain,
    SafetyStatus,
    TaxonomyInfo,
)

logger = logging.getLogger(__name__)

# Cache de resultados BacDive (evita requisições repetidas)
_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)


class BacDiveService:
    """Cliente para a API REST do BacDive."""

    BASE_URL = "https://bacdive.dsmz.de/api/bacdive"

    def __init__(self) -> None:
        settings = get_settings()
        self.email = settings.bacdive_email
        self.password = settings.bacdive_password
        self._client: httpx.AsyncClient | None = None

    # ── Lifecycle ─────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna (e reutiliza) um client HTTP autenticado."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                auth=(self.email, self.password) if self.email else None,
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Busca ─────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search_by_taxonomy(
        self, genus: str, species: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Busca cepas por classificação taxonômica."""
        cache_key = f"tax:{genus}:{species}:{limit}"
        if cache_key in _cache:
            return _cache[cache_key]

        client = await self._get_client()
        query = f"{genus} {species}".strip()

        try:
            resp = await client.get(
                "/taxon/",
                params={"search": query, "format": "json", "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            _cache[cache_key] = results
            logger.info("BacDive taxonomy search '%s': %d results", query, len(results))
            return results
        except httpx.HTTPStatusError as e:
            logger.warning("BacDive API error %s: %s", e.response.status_code, e)
            return []
        except Exception as e:
            logger.error("BacDive connection error: %s", e)
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_strain_by_id(self, bacdive_id: int) -> dict[str, Any] | None:
        """Busca dados completos de uma cepa pelo ID do BacDive."""
        cache_key = f"id:{bacdive_id}"
        if cache_key in _cache:
            return _cache[cache_key]

        client = await self._get_client()

        try:
            resp = await client.get(f"/bacdive_id/{bacdive_id}/", params={"format": "json"})
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                _cache[cache_key] = results[0]
                return results[0]
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("BacDive strain %d error: %s", bacdive_id, e)
            return None
        except Exception as e:
            logger.error("BacDive connection error: %s", e)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search_by_culture_collection(
        self, collection_number: str
    ) -> dict[str, Any] | None:
        """Busca por número de coleção (ex: DSM 17938, ATCC 53103)."""
        cache_key = f"cc:{collection_number}"
        if cache_key in _cache:
            return _cache[cache_key]

        client = await self._get_client()

        try:
            resp = await client.get(
                "/culturecollectionno/",
                params={"search": collection_number, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                _cache[cache_key] = results[0]
                return results[0]
            return None
        except Exception as e:
            logger.error("BacDive culture search error: %s", e)
            return None

    # ── Parsing ───────────────────────────────────────

    @staticmethod
    def parse_growth_conditions(raw: dict[str, Any]) -> GrowthConditions:
        """Extrai condições de crescimento dos dados brutos do BacDive."""
        culture = raw.get("culture_conditions", {})
        temp_data = culture.get("culture_temp", {})
        
        # Temperatura
        temp_opt = 37.0
        temp_min = 15.0
        temp_max = 45.0
        if isinstance(temp_data, list) and temp_data:
            first = temp_data[0] if isinstance(temp_data[0], dict) else {}
            temp_opt = float(first.get("temp", 37))
            temp_min = float(first.get("range_min", temp_opt - 15))
            temp_max = float(first.get("range_max", temp_opt + 10))
        elif isinstance(temp_data, dict):
            temp_opt = float(temp_data.get("temp", 37))

        # pH
        ph_data = culture.get("culture_pH", {})
        ph_opt = 6.5
        ph_min = 4.0
        ph_max = 8.0
        if isinstance(ph_data, list) and ph_data:
            first = ph_data[0] if isinstance(ph_data[0], dict) else {}
            ph_opt = float(first.get("pH", 6.5))
            ph_min = float(first.get("range_min", ph_opt - 2))
            ph_max = float(first.get("range_max", ph_opt + 1.5))
        elif isinstance(ph_data, dict):
            ph_opt = float(ph_data.get("pH", 6.5))

        # Oxigênio
        oxygen = "facultative anaerobe"
        physiology = raw.get("morphology_physiology", {})
        if isinstance(physiology, dict):
            oxygen_data = physiology.get("oxygen_tolerance", {})
            if isinstance(oxygen_data, dict):
                oxygen = oxygen_data.get("oxygen_tol", oxygen)
            elif isinstance(oxygen_data, list) and oxygen_data:
                oxygen = oxygen_data[0].get("oxygen_tol", oxygen)

        return GrowthConditions(
            temperature_min=temp_min,
            temperature_opt=temp_opt,
            temperature_max=temp_max,
            ph_min=ph_min,
            ph_opt=ph_opt,
            ph_max=ph_max,
            oxygen_requirement=oxygen,
        )

    @staticmethod
    def parse_taxonomy(raw: dict[str, Any]) -> TaxonomyInfo:
        """Extrai informações taxonômicas dos dados brutos do BacDive."""
        tax = raw.get("taxonomy_name", {})
        if isinstance(tax, list) and tax:
            tax = tax[0] if isinstance(tax[0], dict) else {}

        return TaxonomyInfo(
            domain=tax.get("domain", "Bacteria"),
            phylum=tax.get("phylum", ""),
            genus=tax.get("genus", "Unknown"),
            species=tax.get("species", ""),
            strain=tax.get("subspecies", ""),
            family=tax.get("family", ""),
            order=tax.get("order", ""),
        )

    def parse_to_strain(
        self, raw: dict[str, Any], bacdive_id: int | None = None
    ) -> ProbioticStrain:
        """Converte dados brutos do BacDive em ProbioticStrain."""
        taxonomy = self.parse_taxonomy(raw)
        growth = self.parse_growth_conditions(raw)
        
        name = f"{taxonomy.genus} {taxonomy.species}"
        if taxonomy.strain:
            name += f" {taxonomy.strain}"

        return ProbioticStrain(
            id=f"bacdive_{bacdive_id or 'unknown'}",
            name=name.strip(),
            taxonomy=taxonomy,
            growth_conditions=growth,
            safety_status=SafetyStatus.UNKNOWN,
            sources=["bacdive"],
            bacdive_id=bacdive_id,
        )

    # ── Busca enriquecida ─────────────────────────────

    async def search_probiotic_strains(
        self, query: str, limit: int = 10
    ) -> list[ProbioticStrain]:
        """
        Busca cepas probióticas no BacDive e retorna como ProbioticStrain.
        Combina busca por taxonomia com parsing dos resultados.
        """
        parts = query.strip().split(maxsplit=1)
        genus = parts[0] if parts else query
        species = parts[1] if len(parts) > 1 else ""

        raw_results = await self.search_by_taxonomy(genus, species, limit)
        strains = []

        for raw in raw_results:
            try:
                # Se temos URLs de detalhes, buscar dados completos
                url = raw.get("url", "")
                bid = None
                if "/bacdive_id/" in str(url):
                    bid = int(str(url).split("/bacdive_id/")[1].strip("/"))
                    detail = await self.get_strain_by_id(bid)
                    if detail:
                        raw = detail

                strain = self.parse_to_strain(raw, bid)
                strains.append(strain)
            except Exception as e:
                logger.warning("Error parsing BacDive result: %s", e)
                continue

        return strains[:limit]
