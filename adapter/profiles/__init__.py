"""MappingProfile loader. Profiles are YAML files in profiles/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

PROFILES_DIR = Path(__file__).resolve().parents[2] / "profiles"


class ConditionMapping(BaseModel):
    label: str
    label_de: str | None = None
    datex2: str
    color: str | None = None


class MappingProfile(BaseModel):
    name: str
    version: str
    description: str = ""
    condition_codes: dict[int, ConditionMapping]
    field_map: dict[str, str] = Field(default_factory=dict)
    horizons: list[str] = Field(default_factory=lambda: ["now", "in_3h", "in_18h"])

    def datex2_for(self, code: int) -> str:
        """Look up the DATEX II enum value for a given AI condition code."""
        mapping = self.condition_codes.get(code) or self.condition_codes[255]
        return mapping.datex2

    def canonical_field(self, source_field: str) -> str | None:
        """Translate a source-specific field name (e.g. 'TEMP') to canonical ('air_temp_c')."""
        return self.field_map.get(source_field)


@lru_cache(maxsize=8)
def load_profile(name: str = "bavaria") -> MappingProfile:
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MappingProfile.model_validate(data)


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES_DIR.glob("*.yaml"))
