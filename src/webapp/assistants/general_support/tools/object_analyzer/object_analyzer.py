# tools/object_analyzer/object_analyzer.py

from .ui import run as ui_run


def run(show_nav: bool = True):
    """
    Start de Object Analyzer UI.
    Alle logica zit in ui.py en ui_logic.py.
    Dit bestand is alleen de entrypoint.
    """
    ui_run(show_nav=show_nav)


# Standalone run (python object_analyzer.py)
if __name__ == "__main__":
    run()


def app():
    """
    Voor multipage Streamlit setups.
    Wordt automatisch aangeroepen door jouw hoofdapp.
    """
    run(show_nav=False)
