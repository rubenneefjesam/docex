# src/webapp/registry.py

from pathlib import Path
import importlib
import traceback

# Basis-map van alle assistants
BASE = Path(__file__).parent / "assistants"

# (Optioneel) overrides als je een afwijkend label of specifieke entrypoints wilt
# voorbeeld:
# OVERRIDES = {
#     "general_support.doc_generator": {
#         "label": "Doc Generator",
#         "entrypoint": "run",  # attribuut in de module
#     }
# }
OVERRIDES: dict[str, dict] = {}


def titleize(name: str) -> str:
    """Maak 'snake_case' mooier leesbaar."""
    return name.replace("_", " ").title()


def resolve_tool_module(asst_key: str, tool_key: str):
    """
    Importeer altijd het package van een tool.
    Als OVERRIDES een entrypoint definieert, geef dat attribuut terug.
    Anders return je gewoon het module-object.
    """
    modname = f"webapp.assistants.{asst_key}.tools.{tool_key}"
    try:
        mod = importlib.import_module(modname)
    except Exception:
        raise ImportError(
            f"Kon module {modname} niet importeren:\n{traceback.format_exc()}"
        )

    # Optioneel: entrypoint kiezen
    ov_key = f"{asst_key}.{tool_key}"
    entry = OVERRIDES.get(ov_key, {}).get("entrypoint")
    if entry:
        if not hasattr(mod, entry):
            raise AttributeError(
                f"Module {modname} heeft geen entrypoint '{entry}'"
            )
        return getattr(mod, entry)

    return mod


def discover_assistants() -> dict:
    """Scan de mappenstructuur en bouw een registry dict op."""
    assistants: dict[str, dict] = {}

    for asst_dir in BASE.iterdir():
        if not asst_dir.is_dir() or asst_dir.name.startswith("__"):
            continue

        asst_key = asst_dir.name
        tools_dir = asst_dir / "tools"
        tools: dict[str, dict] = {}

        if tools_dir.exists():
            for tool_dir in tools_dir.iterdir():
                if not tool_dir.is_dir() or tool_dir.name.startswith("__"):
                    continue

                tool_key = tool_dir.name
                ov_key = f"{asst_key}.{tool_key}"
                override = OVERRIDES.get(ov_key, {})

                tools[tool_key] = {
                    "label": override.get("label", titleize(tool_key)),
                    "resolver": lambda ak=asst_key, tk=tool_key: resolve_tool_module(ak, tk),
                }

        assistants[asst_key] = {
            "label": titleize(asst_key),
            "tools": tools,
        }

    return assistants


# De échte registry
ASSISTANTS = discover_assistants()
