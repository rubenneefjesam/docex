# Auto-generated info module voor de 'calculator_assistant' assistant

def get_calculator_assistant_info():
    return {
        "title": "Calculator Assistant",
        "description": (
            "De Calculator Assistant helpt bij algebra, statistiek en eenhedenconversie, "
            "met snelle en nauwkeurige berekeningen."
        ),
        "tools": [
            {"name": "EquationSolver",   "description": "Lost algebraïsche vergelijkingen op."},
            {"name": "StatisticsEngine", "description": "Voert beschrijvende en inferentiële statistiek uit."},
            {"name": "UnitConverter",    "description": "Zet waardes om tussen verschillende meeteenheden."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('EquationSolver', {'equation':'2*x+3=7'})",
                "explanation": "Lost de vergelijking 2*x+3=7 op voor x."
            }
        ],
    }
