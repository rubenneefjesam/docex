from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Attempt relative import of ui inside this package
try:
    # relative import works when this module is inside the package
    from .ui import run as run_ui
    _IMPORT_ERROR = None
except Exception as _e:
    # keep the error to show it later when someone calls run()
    run_ui = None
    _IMPORT_ERROR = _e

def run(*args, **kwargs):
    """Primary entrypoint expected by some registries. Delegates to ui.run()."""
    if run_ui is None:
        raise RuntimeError(f"UI module could not be imported via relative import. Underlying error: {_IMPORT_ERROR}")
    return run_ui(*args, **kwargs)

def app(*args, **kwargs):
    """Compatibility entrypoint used by the registry; delegates to run()."""
    return run(*args, **kwargs)

def main(*args, **kwargs):
    """Alias for running as a script."""
    return run(*args, **kwargs)

def render(*args, **kwargs):
    """Compatibility alias: some registries expect 'render'."""
    return run(*args, **kwargs)

if __name__ == "__main__":
    main()