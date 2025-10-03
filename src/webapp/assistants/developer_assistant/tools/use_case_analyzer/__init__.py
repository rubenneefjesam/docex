# webapp/assistants/sustainability_advisor/tools/sustainability_extractor/__init__.py

from .story_writer import app

# Maak een alias zodat registry óók ‘run’ kan importeren
run = app
