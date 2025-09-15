# src/webapp/assistants/general_support/tools/doc_comparison/__init__.py

from .doc_comparison import app

# Als je run() of main() hebt, alias die dan ook:
# from .doc_comparison import run, main

# Alias zodat call_tool(render) altijd werkt:
render = app