# webapp/assistants/sustainability_advisor/tools/sustainability_extractor/__init__.py

from .use_case_analyzer import app

# Maak een alias zodat registry óók ‘run’ kan importeren
run = app
