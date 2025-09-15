# src/tools/doc_extractor/__init__.py
"""
Alias-module dat de 'run' functie uit je fysieke bestand 'Document generator.py' laadt
ook als de naam speciale karakters bevat.
"""
import os
import importlib.util

# Bepaal pad naar het scriptbestand
script_name = 'Document generator.py'
script_path = os.path.join(os.path.dirname(__file__), script_name)

# Dynamisch module inladen via importlib
spec = importlib.util.spec_from_file_location('tools.doc_extractor.doc_extractor', script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Alias de 'run' functie naar 'render'
render = getattr(module, 'run')