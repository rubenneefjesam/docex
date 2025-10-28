from pathlib import Path
from typing import Any, Tuple
import importlib
import sys

# Try importing the UI module from both relative and absolute paths
_UI_MODULE_NAME = "your_package.ui"

try:
    ui_module = importlib.import_module(_UI_MODULE_NAME)
    run_ui = getattr(ui_module, "run")
except (ImportError, AttributeError) as e:
    run_ui = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


def run(*args: Any, **kwargs: Any) -> Any:
    """
    Primary entrypoint. Delegates to ui.run().

    Raises:
        RuntimeError: If the UI module cannot be imported or doesn't provide a 'run' function.
    """
    if run_ui is None:
        raise RuntimeError(
            f"Failed to load UI module '{_UI_MODULE_NAME}'. Reason: {_IMPORT_ERROR}"
        )
    return run_ui(*args, **kwargs)


def app(*args: Any, **kwargs: Any) -> Any:
    """
    Compatibility entrypoint for registries. Alias for run().
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
    import sys
    main(*sys.argv[1:])