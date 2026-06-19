"""Auto-discovery registry for Source plug-ins.

Scans the `sources` package for concrete Source subclasses and instantiates one
of each (keyed by `name`). Adding a source file is enough to register it — no
central list to edit. Powers `GET /sources`.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache

import sources as _pkg
from sources.base import Source

_SKIP_MODULES = {"base", "registry"}


@lru_cache(maxsize=1)
def list_sources() -> dict[str, Source]:
    found: dict[str, type[Source]] = {}
    for info in pkgutil.iter_modules(_pkg.__path__):
        if info.name in _SKIP_MODULES:
            continue
        module = importlib.import_module(f"sources.{info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Source)
                and obj is not Source
                and getattr(obj, "name", "")
                and not getattr(obj, "__abstractmethods__", None)
            ):
                found.setdefault(obj.name, obj)
    return {name: cls() for name, cls in sorted(found.items())}


def get_source(name: str) -> Source | None:
    return list_sources().get(name)


def health_report() -> list[dict]:
    return [{"name": name, **src.health()} for name, src in list_sources().items()]
