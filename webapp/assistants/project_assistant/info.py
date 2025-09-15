# Auto-generated info module voor de 'project_assistant' assistant

def get_project_assistant_info():
    return {
        "title": "Project_assistant",
        "description": "Beschrijvingstekst voor de project_assistant assistant."
    }

"""
Assistant: Project Assistant

Beschrijving:
    Helpt met projectplanning, resource-management en voortgangsrapportages.
    Ondersteunt bij het genereren van Gantt‐schema’s, toewijzen van taken
    en automatisch rapporteren van statusupdates.

Tools:
    - TimelinePlanner: genereert Gantt‐schema’s op basis van milestones
    - StatusReporter: maakt automatische voortgangsrapportages
    - TaskAllocator: verdeelt taken over teamleden op basis van beschikbaarheid

Voorbeeld gebruik:
    >>> from assistants.project_assistant.assistant import Assistant
    >>> assistant = Assistant()
    >>> chart = assistant.use_tool('TimelinePlanner', {
    ...     'milestones': [{'name':'Kickoff','date':'2025-05-01'}, ...]
    ... })
    >>> chart.show()
"""

def get_info():
    return {
        "title": "Project Assistant",
        "description": (
            "De Project Assistant ondersteunt projectmanagers bij planning, "
            "resource-toewijzing en rapportages, zodat projecten op tijd "
            "en binnen budget blijven."
        ),
        "tools": [
            {"name": "TimelinePlanner", "description": "Genereert Gantt‐schema’s op basis van opgegeven mijlpalen."},
            {"name": "StatusReporter", "description": "Maakt PDF‐ of HTML‐rapportages van de projectstatus."},
            {"name": "TaskAllocator", "description": "Verdeelt taken automatisch over teamleden."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('TimelinePlanner', {'milestones':[...]})",
                "explanation": "Maakt een visuele planning van projectmijlpalen."
            }
        ],
    }
