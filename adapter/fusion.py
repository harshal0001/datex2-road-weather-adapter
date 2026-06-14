"""Multi-source fusion engine.

Given several sources covering the same road segment, produce ONE fused record by
applying per-field source priority (config-driven, see profiles/fusion.yaml).

This is the interoperability contribution: heterogeneous sources are reconciled
into a single canonical view *before* DATEX II standardization, with full
provenance (which source supplied each field).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

PROFILES_DIR = Path(__file__).resolve().parents[1] / "profiles"


class FusedField(BaseModel):
    value: float | int | str | None
    source: str | None  # which source supplied it (None if no source had it)


class FusionResult(BaseModel):
    segment_id: int
    fields: dict[str, FusedField]          # canonical field -> value + provenance
    sources_used: list[str]                # distinct sources that contributed
    sources_selected: list[str]            # what the caller asked for

    def value(self, field: str):
        f = self.fields.get(field)
        return f.value if f else None

    def provenance(self) -> dict[str, str | None]:
        return {k: v.source for k, v in self.fields.items()}


class FusionProfile(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    source_priority: list[str]
    field_priority: dict[str, list[str]] = {}
    source_fields: dict[str, dict[str, str]] = {}

    def canonical_row(self, source: str, raw: dict) -> dict:
        """Map a source's raw CSV row to canonical field names."""
        mapping = self.source_fields.get(source, {})
        out: dict[str, object] = {}
        for raw_col, canon in mapping.items():
            if raw_col in raw and raw[raw_col] is not None:
                out[canon] = raw[raw_col]
        return out

    def all_fields(self) -> list[str]:
        fields = set(self.field_priority)
        for m in self.source_fields.values():
            fields.update(m.values())
        return sorted(fields)

    def priority_for(self, field: str) -> list[str]:
        return self.field_priority.get(field, self.source_priority)

    def fuse(
        self,
        segment_id: int,
        per_source_raw: dict[str, dict],
        selected: list[str] | None = None,
    ) -> FusionResult:
        """Fuse one segment's per-source raw rows into a single canonical record.

        per_source_raw: {source_name: raw_csv_row_dict}
        selected:       sources the user enabled (default: all in source_priority)
        """
        selected = selected or list(self.source_priority)
        # pre-map every available source's row to canonical fields
        canon_by_source = {
            src: self.canonical_row(src, raw)
            for src, raw in per_source_raw.items()
            if src in selected
        }

        fields: dict[str, FusedField] = {}
        used: set[str] = set()
        for field in self.all_fields():
            chosen = FusedField(value=None, source=None)
            for src in self.priority_for(field):
                if src not in selected:
                    continue
                row = canon_by_source.get(src, {})
                if field in row and row[field] is not None:
                    chosen = FusedField(value=row[field], source=src)
                    used.add(src)
                    break
            fields[field] = chosen

        return FusionResult(
            segment_id=segment_id,
            fields=fields,
            sources_used=[s for s in self.source_priority if s in used],
            sources_selected=selected,
        )


@lru_cache(maxsize=4)
def load_fusion_profile(name: str = "fusion") -> FusionProfile:
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Fusion profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FusionProfile.model_validate(data)
