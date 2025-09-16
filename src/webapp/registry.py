# src/webapp/registry.py

from pathlib import Path
from typing import Dict, Any
import importlib
import traceback

# Basis-map van alle assistants
BASE = Path(__file__).parent / "assistants"

# (Optioneel) overrides per tool:
# voorbeeld:
# OVERRIDES = {
#   "general_support.doc_generator": {
#       "label": "Doc Generator",
#       "entrypoint": "app",  # of "run"
#   }
# }
OVERRIDES: Dict[str, Dict[str, Any]] = {}


def titleize(name: str) -> str:
    """Maak 'snake_case' netjes leesbaar."""
    return name.replace("_", " ").title()


def resolve_tool_module(asst_key: str, tool_key: str):
    """
    Importeer het package van de tool en geef het entrypoint terug.
    Voorkeursvolgorde: override.entrypoint > 'app' > 'run'.
    Raise een duidelijke fout als geen entrypoint gevonden is.
    """
    modname = f"webapp.assistants.{asst_key}.tools.{tool_key}"
    try:
        mod = importlib.import_module(modname)
    except Exception:
        raise ImportError(
            f"Kon module {modname} niet importeren:\n{traceback.format_exc()}"
        )

    ov_key = f"{asst_key}.{tool_key}"
    override = OVERRIDES.get(ov_key, {})
    preferred = override.get("entrypoint")  # optioneel

    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.extend(("app", "run"))

    for candidate in candidates:
        if candidate and hasattr(mod, candidate):
            return getattr(mod, candidate)

    raise AttributeError(
        f"Module {modname} heeft geen geldig entrypoint. "
        f"Geprobeerd: {candidates}"
    )


def discover_assistants() -> Dict[str, Dict[str, Any]]:
    """
    Scan de mappenstructuur onder BASE en bouw een registry dict:
    {
      "<assistant>": {
        "label": "...",
        "tools": {
          "<tool>": {
            "label": "...",
            "resolver": <callable die entrypoint retourneert>
          },
          ...
        }
      },
      ...
    }
    """
    assistants: Dict[str, Dict[str, Any]] = {}

    for asst_dir in BASE.iterdir():
        if not asst_dir.is_dir() or asst_dir.name.startswith("__"):
            continue

        asst_key = asst_dir.name
        tools_dir = asst_dir / "tools"
        tools: Dict[str, Dict[str, Any]] = {}

        if tools_dir.exists():
            for tool_dir in tools_dir.iterdir():
                if not tool_dir.is_dir() or tool_dir.name.startswith("__"):
                    continue

                tool_key = tool_dir.name
                ov_key = f"{asst_key}.{tool_key}"
                override = OVERRIDES.get(ov_key, {})

                # let op: default-args in lambda om late-binding bug te voorkomen
                tools[tool_key] = {
                    "label": override.get("label", titleize(tool_key)),
                    "resolver": (lambda ak=asst_key, tk=tool_key: resolve_tool_module(ak, tk)),
                }

        assistants[asst_key] = {
            "label": titleize(asst_key),
            "tools": tools,
        }

    return assistants


# De échte registry
ASSISTANTS = discover_assistants()
