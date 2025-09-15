# Auto-generated info module voor de 'general_support' assistant

def get_general_support_info():
    return {
        "title": "General_support",
        "description": "Beschrijvingstekst voor de general_support assistant."
    }

"""
Assistant: General Support

Beschrijving:
    Biedt algemene Q&A, helpt bij dagelijkse vragen, agendabeheer
    en simpele workflow-tasks.

Tools:
    - FAQResponder: beantwoordt veelgestelde vragen op basis van een kennisbank
    - CalendarManager: maakt en beheert agendagebeurtenissen
    - WorkflowHelper: automatiseert eenvoudige workflow-stappen

Voorbeeld gebruik:
    >>> from assistants.general_support.assistant import Assistant
    >>> assistant = Assistant()
    >>> answer = assistant.use_tool('FAQResponder', {'question':'Wat is de link naar het HR-portaal?'})
    >>> print(answer)
"""

def get_info():
    return {
        "title": "General Support",
        "description": (
            "De General Support Assistant beantwoordt veelgestelde vragen, "
            "beheert je agenda en ondersteunt bij eenvoudige workflow‐taken."
        ),
        "tools": [
            {"name": "FAQResponder", "description": "Zoekt in de interne kennisbank naar antwoorden."},
            {"name": "CalendarManager", "description": "Beheert agendagebeurtenissen en reminders."},
            {"name": "WorkflowHelper", "description": "Automatiseert repetitieve workflow-stappen."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('FAQResponder', {'question':'Wat is de link naar het HR-portaal?'})",
                "explanation": "Zoekt en geeft het antwoord op een gangbare vraag."
            }
        ],
    }
