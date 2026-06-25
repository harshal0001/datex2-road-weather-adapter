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
    # cross-source view (the basis for the agreement/confidence indicator)
    candidates: dict[str, float | int | str] = {}  # every selected source's value
    agreement: str = "none"   # none | single | agree | spread
    spread: float | None = None  # max-min across numeric candidates (when >1)


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

    def confidence(self) -> dict:
        """Overall fusion confidence from cross-checkable (multi-source) fields."""
        multi = [f for f in self.fields.values() if f.agreement in ("agree", "spread")]
        if not multi:
            return {"level": "single", "agree": 0, "total": 0}
        agree = sum(1 for f in multi if f.agreement == "agree")
        ratio = agree / len(multi)
        level = "high" if ratio >= 0.8 else "medium" if ratio >= 0.5 else "low"
        return {"level": level, "agree": agree, "total": len(multi)}


class FusionProfile(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    source_priority: list[str]
    field_priority: dict[str, list[str]] = {}
    source_fields: dict[str, dict[str, str]] = {}
    # Step 3 — unit harmonization. {source: {raw_col: {factor, offset, clamp}}}
    unit_conversions: dict[str, dict[str, dict]] = {}
    # Per-field absolute tolerance for "sources agree" (canonical units).
    agreement_tolerance: dict[str, float] = {}

    def _agreement(self, field: str, candidates: dict):
        """Classify cross-source agreement for one field's candidate values."""
        vals = list(candidates.values())
        if len(vals) <= 1:
            return ("single" if vals else "none"), None
        nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(nums) == len(vals):                       # all numeric
            spread = max(nums) - min(nums)
            tol = self.agreement_tolerance.get(field)
            if tol is None:                              # sane default if unspecified
                tol = max(0.5, 0.03 * max(abs(x) for x in nums))
            return ("agree" if spread <= tol else "spread"), round(spread, 3)
        return ("agree" if len(set(vals)) == 1 else "spread"), None  # categorical

    def _harmonize(self, source: str, raw_col: str, value):
        """Apply the declared linear unit conversion for a raw column, if any.

        value * factor + offset, then optional clamp. Non-numeric values
        (e.g. condition codes) and unlisted columns pass through unchanged so
        sources are reconciled in a single canonical unit before fusion.
        """
        conv = self.unit_conversions.get(source, {}).get(raw_col)
        if conv is None or not isinstance(value, (int, float)) or isinstance(value, bool):
            return value
        out = value * conv.get("factor", 1.0) + conv.get("offset", 0.0)
        clamp = conv.get("clamp")
        if clamp:
            lo, hi = clamp
            out = max(lo, min(hi, out))
        return out

    def canonical_row(self, source: str, raw: dict) -> dict:
        """Map a source's raw CSV row to canonical field names (with units harmonized)."""
        mapping = self.source_fields.get(source, {})
        out: dict[str, object] = {}
        for raw_col, canon in mapping.items():
            if raw_col in raw and raw[raw_col] is not None:
                out[canon] = self._harmonize(source, raw_col, raw[raw_col])
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
        # None = all sources; [] = explicit empty selection (fuses to no data)
        selected = list(self.source_priority) if selected is None else selected
        # pre-map every available source's row to canonical fields
        canon_by_source = {
            src: self.canonical_row(src, raw)
            for src, raw in per_source_raw.items()
            if src in selected
        }

        fields: dict[str, FusedField] = {}
        used: set[str] = set()
        for field in self.all_fields():
            # every selected source that carries this field is a candidate ...
            candidates = {
                src: canon_by_source[src][field]
                for src in selected
                if field in canon_by_source.get(src, {})
                and canon_by_source[src][field] is not None
            }
            # ... the winner is the first candidate in priority order
            winner = next((s for s in self.priority_for(field) if s in candidates), None)
            if winner is None:
                fields[field] = FusedField(value=None, source=None)
                continue
            used.add(winner)
            agreement, spread = self._agreement(field, candidates)
            fields[field] = FusedField(
                value=candidates[winner], source=winner,
                candidates=candidates, agreement=agreement, spread=spread,
            )

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
