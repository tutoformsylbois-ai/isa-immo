"""Affiche le nombre d'heures écoulées depuis la dernière collecte terminée (9999 s'il n'y en a pas)."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from maisons import base, requetes

cx = base.connexion()
derniere = requetes.derniere_collecte(cx)
cx.close()
if derniere is None:
    print(9999)
else:
    print(round((datetime.now() - datetime.fromisoformat(derniere["fin"])).total_seconds() / 3600, 1))
