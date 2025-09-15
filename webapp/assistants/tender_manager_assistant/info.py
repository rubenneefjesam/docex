# Auto-generated info module voor de 'tender_manager_assistant' assistant

def get_tender_manager_assistant_info():
    return {
        "title": "Tender_manager_assistant",
        "description": "Beschrijvingstekst voor de tender_manager_assistant assistant."
    }

"""
Assistant: Tender Manager Assistant

Beschrijving:
    Beheert aanbestedingsprocessen, bewaakt deadlines, en maakt scoremodellen
    voor inschrijvingen.

Tools:
    - TenderDocumentCreator: genereert complete aanbestedingsdocumenten
    - DeadlineTracker: monitort mijlpalen en stuurt reminders
    - BidScoringModel: evalueert offertes op vooraf gedefinieerde criteria

Voorbeeld gebruik:
    >>> from assistants.tender_manager_assistant.assistant import Assistant
    >>> assistant = Assistant()
    >>> doc = assistant.use_tool('TenderDocumentCreator', {
    ...     'requirements':'RFP.docx'
    ... })
    >>> print(doc.path)
"""

def get_info():
    return {
        "title": "Tender Manager Assistant",
        "description": (
            "De Tender Manager Assistant ondersteunt inkopers en leveranciers "
            "bij het opstellen, beheren en beoordelen van aanbestedingen."
        ),
        "tools": [
            {"name": "TenderDocumentCreator", "description": "Maakt gestandaardiseerde aanbestedingsdocumenten."},
            {"name": "DeadlineTracker", "description": "Stelt reminders in voor belangrijke deadlines."},
            {"name": "BidScoringModel", "description": "Evalueert en rankt offertes volgens criteria."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('TenderDocumentCreator', {'requirements':'RFP.docx'})",
                "explanation": "Genereert een RFP‐document gebaseerd op het sjabloon."
            }
        ],
    }
