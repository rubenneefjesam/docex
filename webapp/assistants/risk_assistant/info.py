# Auto-generated info module voor de 'risk_assistant' assistant

def get_risk_assistant_info():
    return {
        "title": "Risk_assistant",
        "description": "Beschrijvingstekst voor de risk_assistant assistant."
    }

"""
Assistant: Risk Assistant

Beschrijving:
    Identificeert en evalueert projectrisico’s, stelt mitigatiestrategieën voor
    en visualiseert risicoprioriteiten in heatmaps.

Tools:
    - RiskIdentifier: detecteert en classificeert risico’s op basis van jou data
    - HeatmapGenerator: maakt heatmaps voor risicofocus
    - MitigationAdvisor: adviseert over mitigatie‐ en beheersmaatregelen

Voorbeeld gebruik:
    >>> from assistants.risk_assistant.assistant import Assistant
    >>> assistant = Assistant()
    >>> risks = assistant.use_tool('RiskIdentifier', {'project_id': 42})
    >>> print(risks)
"""

def get_info():
    return {
        "title": "Risk Assistant",
        "description": (
            "De Risk Assistant helpt teams bij het identificeren, kwantificeren "
            "en mitigeren van projectrisico’s met data‐gedreven adviezen."
        ),
        "tools": [
            {"name": "RiskIdentifier", "description": "Identificeert risico’s in jouw projectdata."},
            {"name": "HeatmapGenerator", "description": "Visualiseert risicoprioriteiten in een heatmap."},
            {"name": "MitigationAdvisor", "description": "Stelt gerichte mitigatiestrategieën voor."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('RiskIdentifier', {'project_id':123})",
                "explanation": "Haalt een lijst van potentiële risico’s op voor project 123."
            }
        ],
    }
