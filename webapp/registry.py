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
            # optioneel later:
            # "document_extractor": {
            #     "label": "Document extractor",
            #     "page_module": "webapp.assistants.general_support.document_extractor",
            # },
        },
    },
    # toekomstige assistants komen hier bij
}