# webapp/registry.py
ASSISTANTS = {
    "general_support": {
        "label": "General support",
        "tools": {
                "document_generator": {
                    "label": "Document generator",
                    "page_module": "webapp.assistants.general_support.document_generator",
                },
                "document_comparison": {
                    "label": "Document comparison",
                    "page_module": "webapp.assistants.general_support.document_comparison",
                },
        },
    },

    # ——— de overige “ondersteuners” (nu zonder tools; verschijnen wel in de sidebar)
    "tender_assistant": {
        "label": "Tender assistant",
        "tools": {  # later tools toevoegen, nu leeg
        },
    },
    "risk_assistant": {
        "label": "Risk assistant",
        "tools": {
        },
    },
    "calculator_assistant": {
        "label": "Calculator assistant",
        "tools": {
        },
    },
    "legal_assistant": {
        "label": "Legal assistant",
        "tools": {
        },
    },
    "project_assistant": {
        "label": "Project assistant",
        "tools": {
        },
    },
    "sustainability_advisor": {
        "label": "Sustainability advisor",
        "tools": {
        },
    },
}