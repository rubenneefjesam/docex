# src/webapp/registry.py
from pathlib import Path
from typing import Dict, Any
import importlib
import traceback

# (Optioneel) overrides per tool voor zowel assistants als agents
# Keys in form '<namespace>.<key>.<tool>' e.g. 'assistants.general_support.doc_generator'
OVERRIDES: Dict[str, Dict[str, Any]] = {}


def titleize(name: str) -> str:
    """Maak 'snake_case' netjes leesbaar."""
    return name.replace("_", " ").title()


def resolve_tool_module(namespace: str, parent_key: str, tool_key: str) -> Any:
    """
    Importeer het package van een tool uit een gegeven namespace ('assistants' of 'agents')
    en geef de entrypoint terug.
    Prefers OVERRIDES entrypoint, dan attributen 'app' of 'run'.
    """
    modname = f"webapp.{namespace}.{parent_key}.tools.{tool_key}"
    try:
        mod = importlib.import_module(modname)
    except Exception:
        raise ImportError(
            f"Kon module {modname} niet importeren:\n{traceback.format_exc()}"
        )

    ov_key = f"{namespace}.{parent_key}.{tool_key}"
    override = OVERRIDES.get(ov_key, {})
    preferred = override.get("entrypoint")

    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates.extend(("app", "run"))

    for candidate in candidates:
        if candidate and hasattr(mod, candidate):
            return getattr(mod, candidate)

    raise AttributeError(
        f"Module {modname} heeft geen geldig entrypoint. Geprobeerd: {candidates}"
    )


def discover_assistants() -> Dict[str, Dict[str, Any]]:
    """
    Bouw de registry voor assistants:
    mappenstructuur: webapp/assistants/{assistant}/tools/{tool}
    """
    base = Path(__file__).parent / "assistants"
    assistants: Dict[str, Dict[str, Any]] = {}

    for asst_dir in base.iterdir():
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
                tools[tool_key] = {
                    "label": titleize(tool_key),
                    "resolver": (lambda ak=asst_key, tk=tool_key: resolve_tool_module("assistants", ak, tk)),
                }

        assistants[asst_key] = {
            "label": titleize(asst_key),
            "tools": tools,
        }

    return assistants


def discover_agents() -> Dict[str, Dict[str, Any]]:
    """
    Bouw de registry voor agents:
    mappenstructuur: webapp/agents/{agent}/tools/{tool}
    """
    base = Path(__file__).parent / "agents"
    agents: Dict[str, Dict[str, Any]] = {}

    for agent_dir in base.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith("__"):
            continue
        agent_key = agent_dir.name
        tools_dir = agent_dir / "tools"
        tools: Dict[str, Dict[str, Any]] = {}

        if tools_dir.exists():
            for tool_dir in tools_dir.iterdir():
                if not tool_dir.is_dir() or tool_dir.name.startswith("__"):
                    continue
                tool_key = tool_dir.name
                tools[tool_key] = {
                    "label": titleize(tool_key),
                    "resolver": (lambda ak=agent_key, tk=tool_key: resolve_tool_module("agents", ak, tk)),
                }

        agents[agent_key] = {
            "label": titleize(agent_key),
            "tools": tools,
        }

    return agents


# De échte registries
ASSISTANTS = discover_assistants()
AGENTS = discover_agents()