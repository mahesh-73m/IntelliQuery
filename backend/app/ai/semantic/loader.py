from functools import lru_cache
from pathlib import Path

import yaml

_PATH = Path(__file__).with_name("metrics.yaml")


@lru_cache
def load_catalog() -> dict:
    with open(_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def glossary_text(catalog: dict | None = None) -> str:
    c = catalog or load_catalog()
    notes = c["defaults"]["notes"]
    return "\n".join(f"- {g}" for g in c["glossary"] + notes)
