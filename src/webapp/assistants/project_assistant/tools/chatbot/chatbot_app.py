from pathlib import Path
from typing import Any, Optional
import importlib
import sys

# Determine the package for relative import
_package = __package__ if __package__ else Path(__file__).stem
_ui_module_name = f"{_package}.ui"

try:
    ui_module = importlib.import_module(_ui_module_name)
    run_ui = getattr(ui_module, "run")
    _IMPORT_ERROR: Optional[Exception] = None
except Exception as e:
    run_ui = None
    _IMPORT_ERROR = e


def run(*args: Any, **kwargs: Any) -> Any:
    """
    Primary entrypoint. Delegates to ui.run().

    Raises:
        RuntimeError: If the UI module cannot be imported or doesn't provide a 'run' function.
    """
    if run_ui is None:
        raise RuntimeError(
            f"Failed to load UI module '{_ui_module_name}'. Reason: {_IMPORT_ERROR}"
        )
    return run_ui(*args, **kwargs)


def app(*args: Any, **kwargs: Any) -> Any:
    """
    Compatibility entrypoint for registries.
    Alias for run().
    """
    return run(*args, **kwargs)


def main(*args: Any, **kwargs: Any) -> Any:
    """
    Alias for script execution. Equivalent to run().
    """
    return run(*args, **kwargs)


# Some frameworks expect 'render' as the entrypoint name
render = run


if __name__ == "__main__":
    main(*sys.argv[1:])