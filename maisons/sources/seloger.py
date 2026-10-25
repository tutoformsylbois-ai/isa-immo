"""SeLoger : agences, réseaux et quelques particuliers (données JSON intégrées à la page de résultats).
Chaque page de commune montre jusqu'à 30 biens, dont ceux des communes proches quand la commune en a peu."""
import json
import re

import requests

from ..communes import slug
from .commun import nombre, telecharger

NOM = "SeLoger"
BASE = "https://www.seloger.com"
CHEMINS = {"vente": "achat", "location": "locations"}


def collecter(communes, journal=print):
    vues = {}
    for c in communes:
        dep = c["insee"][:2]
        for type_, chemin in CHEMINS.items():
            try:
                _, html = telecharger(f"{BASE}/immobilier/{chemin}/immo-{slug(c['nom'])}-{dep}/bien-maison/")
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 403:
                    # Anti-robot déclenché : on garde ce qui a été lu (les annonces non revues ne seront pas retirées).
                    journal(f"!! {NOM} : bloqué à {c['nom']}, collecte partielle ({len(vues)} annonces)")
                    return list(vues.values())
                raise
            if html is None:
                continue
            for a in lire_page(html, type_):
                vues[a["source_id"]] = a
        journal(f"  {NOM} {c['nom']:35} total {len(vues)}")
    return list(vues.values())


def donnees(html):
    m = re.search(r'window\["__UFRN_FETCHER__"\]=JSON\.parse\((".*?")\);?\s*</script>', html, re.S)
    if not m:
        return {}
    return json.loads(json.loads(m.group(1)))


def lire_page(html, type_):
    serp = donnees(html).get("data", {}).get("classified-serp-data", {})
    annonces = []
    for c in (serp.get("classifiedsData") or {}).values():
        a = lire(c, type_)
        if a:
            annonces.append(a)
    return annonces


def lire(c, type_):
    suivi = c.get("tracking") or {}
    fournisseur = c.get("provider") or {}
    if (suivi.get("building_state") in ("PROJECTED", "NEW_BUILD") or fournisseur.get("publisherType") == "BUILDER"
            or "construire" in (c.get("url") or "")):
        return None  # offres de constructeurs
    faits = {f.get("type"): f.get("splitValue") for f in (c.get("hardFacts") or {}).get("facts", [])}
    adresse = (c.get("location") or {}).get("address") or {}
    images = (c.get("gallery") or {}).get("images") or []
    if fournisseur.get("isPrivateOwner"):
        agence = "Particulier"
    else:
        agence = ((fournisseur.get("intermediaryCard") or {}).get("title")
                  or (c.get("cardProvider") or {}).get("title") or "Professionnel")
        agence = re.sub(r"\s+", " ", agence).strip()
        if fournisseur.get("publisherType") == "NOTARY" and "notaire" not in agence.lower():
            agence = f"Notaire – {agence}"
    contact = " · ".join(x for x in [fournisseur.get("address"), (fournisseur.get("phoneNumbers") or [None])[0]] if x)
    return {
        "source": NOM,
        "source_id": c["id"],
        "url": c.get("url") or f"{BASE}/annonces/{c['id']}",
        "type": type_,
        "titre": (c.get("hardFacts") or {}).get("title") or "Maison",
        "prix": suivi.get("price") or nombre(re.sub(r"[^\d]", "", ((c.get("hardFacts") or {}).get("price") or {}).get("value") or "")),
        "surface": nombre(faits.get("livingSpace") or faits.get("overallSpace")),
        "pieces": nombre(faits.get("numberOfRooms")),
        "chambres": nombre(faits.get("numberOfBedrooms")),
        "terrain": nombre(faits.get("plotSpace")),
        "commune": adresse.get("city"),
        "code_postal": adresse.get("zipCode"),
        "agence": agence,
        "agence_contact": contact or None,
        "dpe": None,
        "photo": images[0].get("url") if images else None,
        "description": ((c.get("mainDescription") or {}).get("description") or "")[:600],
    }
