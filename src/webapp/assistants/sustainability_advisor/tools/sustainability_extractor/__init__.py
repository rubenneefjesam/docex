# Zorgt dat het package een callable 'app' (en alias 'run') exporteert
from .sustainability_extractor import app, run

__all__ = ["app", "run"]