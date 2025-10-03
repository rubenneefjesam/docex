# Auto-generated info module voor de 'risk_assistant' assistant

def get_developer_assistant_info():
    return {
        "title": "Developer Assitstant",
        "description": (
            "Deze assistant helpt je met de comments schrijven en "
            "je code uit te leggen in de code"
        ),
        "tools": [
            {"name": "RiskIdentifier",   "description": "Identificeert risico’s in jouw projectdata."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('RiskIdentifier', {'project_id':123})",
                "explanation": "Haalt een lijst van potentiële risico’s op voor project 123."
            }
        ],
    }
