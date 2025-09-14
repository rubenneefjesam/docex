# webapp/assistants/home/__init__.py
# Package initializer for assistants.home. Expose the main render() if available.

# primary home renderer (from home.home)
try:
    from .home import render as render
except Exception:
    def render():
        raise ImportError("Could not import 'render' from webapp.assistants.home.home")

# optional convenience aliases for info/contact
try:
    from .info import render as render_info
except Exception:
    render_info = None

try:
    from .contact import render as render_contact
except Exception:
    render_contact = None
