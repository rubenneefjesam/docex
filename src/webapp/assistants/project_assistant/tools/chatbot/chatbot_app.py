from pathlib import Path

# Attempt to import the UI module (ui.py lives in same folder)
try:
    # Prefer a function named 'run' from ui if present.
    from ui import run as run_ui
    _IMPORT_ERROR = None
except Exception as _e:
    run_ui = None
    _IMPORT_ERROR = _e

def run(*args, **kwargs):
    """Primary entrypoint expected by some registries. Delegates to ui.run()."""
    if run_ui is None:
        raise RuntimeError(f"UI module could not be imported. Underlying error: {_IMPORT_ERROR}")
    return run_ui(*args, **kwargs)

def app(*args, **kwargs):
    """Compatibility entrypoint used by the registry; delegates to run()."""
    return run(*args, **kwargs)

def main(*args, **kwargs):
    """Simple alias for running as a script."""
    return run(*args, **kwargs)

def render(*args, **kwargs):
    """Compatibility alias: some registries expect a 'render' symbol."""
    return run(*args, **kwargs)

if __name__ == "__main__":
    main()