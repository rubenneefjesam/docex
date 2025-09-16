# sitecustomize.py - wordt automatisch geladen door Python's 'site' module
import sys, os

ROOT = os.path.realpath(os.path.dirname(__file__))     # projectroot
SRC  = os.path.join(ROOT, "src")                       # .../src

if SRC not in sys.path:
    sys.path.insert(0, SRC)
