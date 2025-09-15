# Auto-generated info module voor de 'legal_assistant' assistant

def get_legal_assistant_info():
    return {
        "title": "Legal Assistant",
        "description": (
            "De Legal Assistant ondersteunt bij contractanalyse, compliance-checks "
            "en zoekt relevante jurisprudentie om juridische risico’s te verkleinen."
        ),
        "tools": [
            {"name": "ContractAnalyzer",   "description": "Analyseert contractteksten op clausules en risico’s."},
            {"name": "ComplianceChecker",  "description": "Toetst documenten aan geldende wet- en regelgeving."},
            {"name": "CaseLawSearch",      "description": "Zoekt relevante jurisprudentie op basis van onderwerpen."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('ContractAnalyzer', {'document':'overeenkomst.pdf'})",
                "explanation": "Analyseert de gegeven overeenkomst op belangrijke clausules."
            }
        ],
    }
