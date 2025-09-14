# webapp/assistants/home/__init__.py
# Expose the main render function for the package, mapping to home.home.render
try:
    from .home import render as render
except Exception:
    # fallback: don't crash import if the inner module changes; provide a helpful message
    def render():
        raise ImportError("Could not import 'render' from webapp.assistants.home.home")
# also keep references to info/contact renderers if needed
try:
    from .info import render as render_info
except Exception:
    render_info = None

try:
    from .contact import render as render_contact
except Exception:
    render_contact = None
