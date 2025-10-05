from pathlib import Path

# attempt to import the UI module (ui.py lives in same folder)
try:
    from ui import run as run_ui
except Exception as e:
    run_ui = None
    _IMPORT_ERROR = e

def app():
    """Compatibility entrypoint used by the registry."""
    if run_ui is None:
        raise RuntimeError(f"UI module could not be imported: {_IMPORT_ERROR}")
    return run_ui()

def main():
    return app()

# Provide a render alias for registries that expect render()
def render(*args, **kwargs):
    return app()

if __name__ == "__main__":
    main()