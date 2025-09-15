# Auto-generated info module voor de 'calculator_assistant' assistant

def get_calculator_assistant_info():
    return {
        "title": "Calculator_assistant",
        "description": "Beschrijvingstekst voor de calculator_assistant assistant."
    }

"""
Assistant: Calculator Assistant

Beschrijving:
    Voert complexe wiskundige berekeningen uit, lost vergelijkingen op
    en kan statistische analyses draaien.

Tools:
    - EquationSolver: lost algebraïsche vergelijkingen en stelsels op
    - StatisticsEngine: berekent gemiddelden, varianties en regressies
    - UnitConverter: zet eenheden om tussen SI- en imperialsystemen

Voorbeeld gebruik:
    >>> from assistants.calculator_assistant.assistant import Assistant
    >>> assistant = Assistant()
    >>> result = assistant.use_tool('EquationSolver', {'equation':'2*x+3=7'})
    >>> print(result)  # {'x':2}
"""

def get_info():
    return {
        "title": "Calculator Assistant",
        "description": (
            "De Calculator Assistant helpt bij algebra, statistiek en eenhedenconversie, "
            "met snelle en nauwkeurige berekeningen."
        ),
        "tools": [
            {"name": "EquationSolver", "description": "Lost algebraïsche vergelijkingen op."},
            {"name": "StatisticsEngine", "description": "Voert beschrijvende en inferentiële statistiek uit."},
            {"name": "UnitConverter", "description": "Zet waardes om tussen verschillende meeteenheden."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('EquationSolver', {'equation':'2*x+3=7'})",
                "explanation": "Lost de vergelijking 2*x+3=7 op voor x."
            }
        ],
    }
