
# Expose canonical entrypoint used by webapp
# We import safely and fall back to None if import fails so package remains importable.
try:
    from .speech_2_document import run as docgen
except Exception:
    docgen = None
