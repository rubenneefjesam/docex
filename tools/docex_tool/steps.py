# tools/docex_tool/steps.py
from typing import List
_steps: List[str] = []

def clear_steps():
    global _steps
    _steps = []

def record_step(msg: str):
    _steps.append(msg)

def get_steps() -> List[str]:
    return list(_steps)

def steps_as_text(prefix: str = "Uitgevoerde stappen:") -> str:
    lines = [prefix] + [f"- {s}" for s in _steps]
    return "\n".join(lines)
