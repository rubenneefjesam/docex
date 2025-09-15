
# Expose the coge tool entrypoint so webapp can call package-level attributes.
# We import defensively so the package remains importable even if coge fails.
try:
    from .doc_comparison import app as app
    from .doc_comparison import app as coge
except Exception:
    # fallback: keep names defined so loader can detect None and show a friendly error
    app = None
    doc_comparison = None
