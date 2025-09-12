# tools/docex_tool/steps.py
"""
Eenvoudige in-memory logger voor stappen die tijdens een run worden uitgevoerd.
Kan gebruikt worden in de UI en om een overzicht in het .docx te schrijven.
"""
from typing import List

_steps: List[str] = []

def clear_steps():
    global _steps
    _steps = []

def record_step(msg: str):
    """Voeg 1 stap toe (string)."""
    _steps.append(msg)

def get_steps() -> List[str]:
    """Retourneer alle geregistreerde stappen (kopie)."""
    return list(_steps)

def steps_as_text(prefix: str = "Uitgevoerde stappen:") -> str:
    lines = [prefix] + [f"- {s}" for s in _steps]
    return "\n".join(lines)
