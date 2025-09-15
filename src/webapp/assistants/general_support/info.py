# Auto-generated info module voor de 'general_support' assistant

def get_general_support_info():
    return {
        "title": "General Support",
        "description": (
            "De General Support Assistant beantwoordt veelgestelde vragen, "
            "beheert je agenda en ondersteunt bij eenvoudige workflow-taken."
        ),
        "tools": [
            {"name": "FAQResponder",    "description": "Zoekt in de interne kennisbank naar antwoorden."},
            {"name": "CalendarManager", "description": "Beheert agendagebeurtenissen en reminders."},
            {"name": "WorkflowHelper",  "description": "Automatiseert repetitieve workflow-stappen."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('FAQResponder', {'question':'Wat is de link naar het HR-portaal?'})",
                "explanation": "Zoekt en geeft het antwoord op een gangbare vraag."
            }
        ],
    }
