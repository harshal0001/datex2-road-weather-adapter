"""DATEX II XSD validation gate.

Validates serialized DATEX II XML against the official v3.4 schema
(`schemas/DATEXII_3_Profile/DATEXII_3_D2Payload.xsd`, whose root element is
`<payload>` of abstract type PayloadPublication). The schema (with all its imports)
is loaded once and cached — construction is the slow part.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SCHEMA_ROOT = (
    Path(__file__).resolve().parents[1]
    / "schemas" / "DATEXII_3_Profile" / "DATEXII_3_D2Payload.xsd"
)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]

    @property
    def status(self) -> str:
        return "valid" if self.valid else "invalid"


@lru_cache(maxsize=1)
def _schema():
    import xmlschema

    if not SCHEMA_ROOT.exists():
        raise FileNotFoundError(
            f"DATEX II schema not found at {SCHEMA_ROOT} — the schemas/ bundle is missing."
        )
    return xmlschema.XMLSchema(str(SCHEMA_ROOT))


def validate(xml: str | bytes, max_errors: int = 25) -> ValidationResult:
    """Validate a DATEX II XML document against the official XSD."""
    schema = _schema()
    errors: list[str] = []
    for err in schema.iter_errors(xml):
        # reason + the offending path is the useful part
        path = getattr(err, "path", None)
        errors.append(f"{path}: {err.reason}" if path else str(err.reason or err))
        if len(errors) >= max_errors:
            break
    return ValidationResult(valid=not errors, errors=errors)


def is_valid(xml: str | bytes) -> bool:
    return validate(xml).valid
