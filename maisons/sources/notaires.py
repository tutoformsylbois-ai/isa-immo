"""Immobilier.notaires.fr : biens vendus ou loués par les notaires (service JSON du site, par département)."""
import json
from urllib.parse import urlencode

import requests

from .commun import telecharger

NOM = "Notaires"
API = "https://www.immobilier.notaires.fr/pub-services/inotr-www-annonces/v1/annonces"
OFFICES = "https://www.immobilier.notaires.fr/pub-services/inotr-consultation-offices/v1/offices"
TYPES = {"vente": "VENTE", "location": "LOCATION"}
PAR_PAGE = 100
PAGES_MAX = 20


def collecter(communes, journal=print):
    departements = ",".join(sorted({c["insee"][:2] for c in communes}))
    annonces = []
    for type_, code in TYPES.items():
        for page in range(1, PAGES_MAX + 1):
            params = {"typeTransactions": code, "typeBiens": "MAI", "departements": departements,
                      "offset": (page - 1) * PAR_PAGE, "page": page, "parPage": PAR_PAGE, "perimetre": 0}
            _, texte = telecharger(f"{API}?{urlencode(params)}", entetes={"Accept": "application/json"})
            if texte is None:
                break
            d = json.loads(texte)
            # Le service renvoie parfois des locations avec les ventes : on se fie au type de chaque annonce.
            annonces += [lire(a, "location" if a.get("typeTransaction") == "LOCATION" else "vente")
                         for a in d.get("annonceResumeDto", []) if a.get("ancienNeuf") != "NEUF"]
            if page >= d.get("nbPages", 0):
                break
        journal(f"  {NOM} {type_:8} départements {departements} : {len(annonces)} annonces")
    # Nom et adresse de l'office, pour les seules annonces des secteurs (un appel par office).
    secteurs, offices = {c["insee"] for c in communes}, {}
    for a in annonces:
        if a["insee"] in secteurs and a["crpcen"]:
            if a["crpcen"] not in offices:
                offices[a["crpcen"]] = office(a["crpcen"])
            nom, adresse = offices[a["crpcen"]]
            a["agence"] = nom or a["agence"]
            a["agence_contact"] = " · ".join(x for x in [adresse, a["agence_contact"]] if x) or None
    return list({a["source_id"]: a for a in annonces}.values())


def office(crpcen):
    """('Notaires Ludovic LIVERNETTE et Antoine CHARLES', '36200 Saint-Marcel') ou (None, None)."""
    try:
        _, texte = telecharger(f"{OFFICES}?crpcen={crpcen}", entetes={"Accept": "application/json"})
        o = json.loads(texte) if texte else {}
    except (ValueError, requests.RequestException):
        return None, None
    nom = " ".join((o.get("intitule") or "").split())
    ville = " ".join((o.get("adrGeoVille") or "").split()).title()
    return (f"Notaires {nom}" if nom else None), " ".join(x for x in [o.get("adrGeoCodePostal"), ville] if x) or None


def lire(a, type_):
    tel = a.get("telephone") or ""
    tel = " ".join(tel[i:i + 2] for i in range(0, len(tel), 2)) if tel.isdigit() else tel
    return {
        "source": NOM,
        "source_id": str(a["annonceId"]),
        "url": a.get("urlDetailAnnonceFr"),
        "type": type_,
        "titre": f"Maison {a['nbPieces']} pièces" if a.get("nbPieces") else "Maison",
        # Prix frais de négociation du notaire compris, comme dans les annonces d'agences.
        "prix": a.get("prixTotal") or a.get("prixAffiche"),
        "surface": a.get("surface"),
        "pieces": a.get("nbPieces"),
        "chambres": a.get("nbChambres"),
        "terrain": a.get("surfaceTerrain"),
        "commune": a.get("communeNom"),
        "code_postal": a.get("codePostal"),
        "insee": a.get("inseeCommune"),
        "agence": f"Notaire (office {a['crpcen']})" if a.get("crpcen") else "Notaire",
        "crpcen": a.get("crpcen"),
        "agence_contact": tel or None,
        "dpe": None,
        "photo": a.get("urlPhotoPrincipale"),
        "description": (a.get("descriptionFr") or "")[:600],
    }
