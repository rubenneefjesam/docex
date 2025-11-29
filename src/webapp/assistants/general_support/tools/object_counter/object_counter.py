# tools/object_counter/object_counter.py

from .ui import run as ui_run


def run(show_nav: bool = True):
    """
    Start de object counter UI.
    Alle logica zit in ui.py en ui_logic.py.
    Dit bestand is alleen de entrypoint.
    """
    ui_run(show_nav=show_nav)


# Standalone execution (bijv. python object_counter.py)
if __name__ == "__main__":
    run()


def app():
    """
    Voor jouw multipage Streamlit omgeving
    (bijv. wanneer dit onderdeel is van een grotere Streamlit app).
    """
    run(show_nav=False)
