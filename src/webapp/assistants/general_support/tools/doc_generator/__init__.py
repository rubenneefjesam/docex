# src/webapp/assistants/general_support/tools/doc_generator/__init__.py

from .doc_generator import app

# Optioneel ook run/main als je die hebt:
# from .doc_generator import run, main

# Alias zodat call_tool(render) altijd werkt:
render = app