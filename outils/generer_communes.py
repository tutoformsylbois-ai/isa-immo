"""Génère data/communes.json : les communes des secteurs suivis.

  - Argenton-sur-Creuse, puis les couronnes de 0 à 10 km, 10 à 20 km et 20 à 30 km autour d'Argenton ;
  - les communes à moins de 10 km d'Azerables (23160) ;
  - les communes à moins de 10 km de Liglet (86290).
Une commune peut appartenir à plusieurs secteurs (champ « zones »).

Contours des communes : dépôt france-geojson (GitHub), centres et codes postaux : géocodeur IGN.
À relancer seulement si on change les secteurs, puis relancer zones_bienici.py.
"""
import json
import math
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from maisons.communes import CENTRES, COURONNES, INSEE_ARGENTON

DEPARTEMENTS = ["36-indre", "23-creuse", "86-vienne", "87-haute-vienne"]

GEOJSON = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements/{dep}/communes-{dep}.geojson"
GEOCODEUR = "https://data.geopf.fr/geocodage/search"

SORTIE = Path(__file__).resolve().parent.parent / "data" / "communes.json"


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def centre(geometrie):
    """Centre approximatif : moyenne des points du contour extérieur."""
    anneaux = geometrie["coordinates"]
    if geometrie["type"] == "MultiPolygon":
        anneaux = max(anneaux, key=lambda p: len(p[0]))
    points = anneaux[0]
    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lat, lon


def geocoder(nom, insee=None, code_postal=None):
    params = {"q": nom, "type": "municipality", "limit": 1}
    if insee:
        params["citycode"] = insee
    if code_postal:
        params["postcode"] = code_postal
    r = requests.get(GEOCODEUR, params=params, timeout=30)
    r.raise_for_status()
    features = r.json().get("features", [])
    return features[0] if features else None


def zones(insee, d):
    """d = {centre: distance}. Renvoie la liste des secteurs de la commune."""
    z = []
    if insee == INSEE_ARGENTON:
        z.append("argenton")
    else:
        for cle, mini, maxi in COURONNES:
            if mini < d["argenton"] <= maxi:
                z.append(cle)
    z += [cle for cle, c in CENTRES.items() if cle != "argenton" and d[cle] <= c["rayon_km"]]
    return z


def main():
    points = {}
    for cle, c in CENTRES.items():
        f = geocoder(c["nom"], code_postal=c["code_postal"])
        lon, lat = f["geometry"]["coordinates"]
        points[cle] = (lat, lon)
        print(f"Centre {c['nom']} : {lat:.4f}, {lon:.4f}")

    communes = []
    for dep in DEPARTEMENTS:
        r = requests.get(GEOJSON.format(dep=dep), timeout=60)
        r.raise_for_status()
        for f in r.json()["features"]:
            lat, lon = centre(f["geometry"])
            d = {cle: round(distance_km(p, (lat, lon)), 1) for cle, p in points.items()}
            z = zones(f["properties"]["code"], d)
            if z:
                communes.append({
                    "nom": f["properties"]["nom"],
                    "insee": f["properties"]["code"],
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                    "distance_km": d["argenton"],
                    "distances": d,
                    "zones": z,
                })
    for c in communes:
        f = geocoder(c["nom"], insee=c["insee"])
        c["code_postal"] = f["properties"].get("postcode") if f else None
        if f:  # les contours donnent « Trimouille », le géocodeur « La Trimouille »
            c["nom"] = f["properties"].get("city") or f["properties"].get("name") or c["nom"]
        time.sleep(0.2)
    communes.sort(key=lambda c: c["distance_km"])
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps(communes, ensure_ascii=False, indent=1), encoding="utf-8")
    for cle in ["argenton", *(c[0] for c in COURONNES), *(k for k in CENTRES if k != "argenton")]:
        print(f"{cle:10} {sum(cle in c['zones'] for c in communes)} communes")
    print(f"{len(communes)} communes -> {SORTIE}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
