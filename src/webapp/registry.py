# src/webapp/registry.py

from pathlib import Path

# Basis-map van al je assistants
BASE = Path(__file__).parent / "assistants"

# (Optioneel) hier kun je per assistant.tool key overrides definiëren:
# OVERRIDES["general_support.document_generator"] = {
#     "label": "My Special Doc-Gen",
#     "page_module_candidates": [
#         "custom.path.to.module",
#         "another.fallback.path",
#     ],
# }
OVERRIDES: dict[str, dict] = {}

def titleize(name: str) -> str:
    """Vervang underscores door spaties en zet elk woord met hoofdletter."""
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
                # standaard paden: module.py en map/
                default_candidates = [
                    f"{module_base}.{tool_key}",
                    module_base
                ]

                # zie of we overrides hebben voor label of andere paden
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

# Dit is je nieuwe registry:
ASSISTANTS = discover_assistants()
