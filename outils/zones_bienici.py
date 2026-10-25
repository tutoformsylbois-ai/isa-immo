"""Ajoute à data/communes.json l'identifiant de zone Bien'ici de chaque commune (champ bienici_zone).
À relancer seulement après generer_communes.py."""
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from maisons.communes import FICHIER
from maisons.sources.commun import ENTETES


def main():
    communes = json.loads(FICHIER.read_text(encoding="utf-8"))
    for c in communes:
        trouve = None
        # Un nom porté par plusieurs communes (Saint-Marcel…) se départage avec le code postal.
        for q in (c["nom"], f"{c['nom']} {c.get('code_postal') or ''}".strip()):
            r = requests.get("https://res.bienici.com/suggest.json", params={"q": q}, headers=ENTETES, timeout=20)
            r.raise_for_status()
            trouve = next((z for z in r.json() if z.get("insee_code") == c["insee"]), None)
            if trouve:
                break
        c["bienici_zone"] = trouve["zoneIds"][0] if trouve and trouve.get("zoneIds") else None
        print(f"{c['nom']:30} {c['bienici_zone']}")
        time.sleep(0.5)
    FICHIER.write_text(json.dumps(communes, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
