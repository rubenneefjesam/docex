# Auto-generated info module voor de 'tender_manager_assistant' assistant

def get_tender_manager_assistant_info():
    return {
        "title": "Tender Manager Assistant",
        "description": (
            "De Tender Manager Assistant ondersteunt inkopers en leveranciers "
            "bij het opstellen, beheren en beoordelen van aanbestedingen."
        ),
        "tools": [
            {"name": "TenderDocumentCreator","description": "Maakt gestandaardiseerde aanbestedingsdocumenten."},
            {"name": "DeadlineTracker",      "description": "Stelt reminders in voor belangrijke deadlines."},
            {"name": "BidScoringModel",      "description": "Evalueert en rankt offertes volgens criteria."}
        ],
        "examples": [
            {
                "code": "assistant.use_tool('TenderDocumentCreator', {'requirements':'RFP.docx'})",
                "explanation": "Genereert een RFP-document gebaseerd op het sjabloon."
            }
        ],
    }
