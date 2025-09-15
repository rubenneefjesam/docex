# Auto-generated info module voor de 'project_assistant' assistant

def get_project_assistant_info():
    return {
        "title": "Project Assistant",
        "description": (
            "De Project Assistant ondersteunt projectmanagers bij planning, "
            "resource-toewijzing en rapportages, zodat projecten op tijd "
            "en binnen budget blijven."
        ),
        "tools": [
            {"name": "TimelinePlanner",  "description": "Genereert Gantt-schema’s op basis van opgegeven mijlpalen."},
            {"name": "StatusReporter",   "description": "Maakt PDF- of HTML-rapportages van de projectstatus."},
            {"name": "TaskAllocator",    "description": "Verdeelt taken automatisch over teamleden."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('TimelinePlanner', {'milestones':[{'name':'Kickoff','date':'2025-05-01'}]})",
                "explanation": "Maakt een visuele planning van projectmijlpalen."
            }
        ],
    }
