"""Secteurs suivis, communes qui les composent et rattachement d'une annonce à l'une d'elles."""
import json
import re
import unicodedata
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "data" / "communes.json"
INSEE_ARGENTON = "36006"

# Centres des secteurs (les communes à moins de rayon_km du centre en font partie).
CENTRES = {
    "argenton": {"nom": "Argenton-sur-Creuse", "code_postal": "36200", "rayon_km": 30},
    "azerables": {"nom": "Azerables", "code_postal": "23160", "rayon_km": 10},
    "liglet": {"nom": "Liglet", "code_postal": "86290", "rayon_km": 10},
}
# Couronnes autour d'Argenton (Argenton lui-même forme le secteur « argenton »).
COURONNES = [("r10", 0, 10), ("r20", 10, 20), ("r30", 20, 30)]

LIBELLES_ZONES = {
    "argenton": "Argenton-sur-Creuse",
    "r10": "Argenton 10 km",
    "r20": "Argenton 10 à 20 km",
    "r30": "Argenton 20 à 30 km",
    "azerables": "Azerables (10 km)",
    "liglet": "Liglet (10 km)",
}


def normaliser(nom):
    """'Le Pêchereau' -> 'pechereau', 'St-Marcel' -> 'saint marcel'."""
    s = unicodedata.normalize("NFD", nom.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[-'’]", " ", s)
    s = re.sub(r"\bst\b", "saint", s)
    s = re.sub(r"\bste\b", "sainte", s)
    s = re.sub(r"^(le|la|les|l)\s+", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def slug(nom):
    """Nom pour les adresses des sites : 'La Châtre-Langlin' -> 'la-chatre-langlin'."""
    s = unicodedata.normalize("NFD", nom.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8"))


class Repertoire:
    def __init__(self):
        self.communes = charger()
        self._par_insee = {c["insee"]: c for c in self.communes}
        self._par_nom = {}
        for c in self.communes:
            self._par_nom.setdefault(normaliser(c["nom"]), []).append(c)

    def trouver(self, nom, code_postal=None, insee=None):
        """Renvoie la commune (dict) si elle est dans un secteur suivi, sinon None.
        Deux communes du même nom (dans deux départements) se départagent avec le code postal."""
        if insee:
            return self._par_insee.get(str(insee))
        if not nom:
            return None
        candidates = self._par_nom.get(normaliser(nom), [])
        if len(candidates) > 1 and code_postal:
            candidates = [c for c in candidates if (c.get("code_postal") or "")[:2] == str(code_postal)[:2]] or candidates
        return candidates[0] if candidates else None

    @staticmethod
    def zone(commune):
        """Secteurs de la commune, séparés par des virgules (ex. 'r30,azerables')."""
        return ",".join(commune["zones"])
