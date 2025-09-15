# src/webapp/registry.py

from pathlib import Path

# Basis-map van al je assistants
BASE = Path(__file__).parent / "assistants"

# (Optioneel) overrides als je een afwijkende label of extra paden nodig hebt
OVERRIDES: dict[str, dict] = {}

def titleize(name: str) -> str:
    return name.replace("_", " ").title()

def discover_assistants() -> dict:
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
                module_base = f"webapp.assistants.{asst_key}.tools.{tool_key}"
                default_candidates = [
                    f"{module_base}.{tool_key}",
                    module_base
                ]

                ov_key = f"{asst_key}.{tool_key}"
                override = OVERRIDES.get(ov_key, {})

                tools[tool_key] = {
                    "label": override.get("label", titleize(tool_key)),
                    "page_module_candidates": override.get("page_module_candidates", default_candidates)
                }

        assistants[asst_key] = {
            "label": titleize(asst_key),
            "tools": tools
        }

    return assistants

# De échte registry
ASSISTANTS = discover_assistants()
