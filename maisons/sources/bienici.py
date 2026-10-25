"""Bien'ici : annonces des agences et mandataires (données JSON de son moteur de recherche)."""
import json
import re
from pathlib import Path

import requests

from .commun import telecharger

NOM = "Bien'ici"
API = "https://www.bienici.com/realEstateAds.json?filters="
DETAIL = "https://www.bienici.com/realEstateAd.json?id="
CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "agences_bienici.json"
PAR_PAGE = 100
PAGES_MAX = 20
TYPES = {"vente": "buy", "location": "rent"}
VENDEURS = {"agency": "Agence", "mandatary": "Mandataire", "private": "Particulier"}


def collecter(communes, journal=print):
    zones = [c["bienici_zone"] for c in communes if c.get("bienici_zone")]
    annonces = []
    for type_, filtre in TYPES.items():
        lues = 0
        for page in range(PAGES_MAX):
            filtres = {"size": PAR_PAGE, "from": page * PAR_PAGE, "filterType": filtre, "propertyType": ["house"],
                       "sortBy": "publicationDate", "sortOrder": "desc", "onTheMarket": [True],
                       "zoneIdsByTypes": {"zoneIds": zones}}
            _, texte = telecharger(API + requests.utils.quote(json.dumps(filtres)))
            if texte is None:
                break
            d = json.loads(texte)
            for a in d.get("realEstateAds", []):
                lues += 1
                if not a.get("newProperty"):  # les offres de constructeurs sont ignorées
                    annonces.append((a, lire(a, type_)))
            if (page + 1) * PAR_PAGE >= d.get("total", 0):
                break
        journal(f"  {NOM} {type_:8} {lues} annonces")
    agences = Agences()
    for brute, a in annonces:
        a["agence"], a["agence_contact"] = agences.vendeur(brute)
    agences.enregistrer()
    journal(f"  {NOM} {len(agences.fiches)} agences connues")
    return [a for _, a in annonces]


class Agences:
    """La liste de résultats ne donne pas le nom du vendeur ; le détail d'une annonce, si.
    On lit donc une annonce par compte vendeur, une seule fois : les noms sont gardés dans data/agences_bienici.json."""

    def __init__(self):
        self.fiches = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    def vendeur(self, a):
        genre = VENDEURS.get(a.get("accountType"), "Professionnel")
        if genre == "Particulier":
            return genre, None
        compte = ((a.get("userRelativeData") or {}).get("accountIds") or [None])[0]
        if compte and compte not in self.fiches:
            self.fiches[compte] = self._lire(a["id"])
        fiche = self.fiches.get(compte) or {}
        return fiche.get("nom") or genre, fiche.get("contact")

    @staticmethod
    def _lire(id_annonce):
        try:
            _, texte = telecharger(DETAIL + requests.utils.quote(id_annonce))
        except requests.RequestException:
            return None  # on réessaiera à la prochaine collecte
        if texte is None:
            return None
        c = json.loads(texte).get("contactRelativeData") or {}
        nom = re.sub(r"\s*/\s*", " – ", c.get("agencyNameToDisplay") or c.get("contactNameToDisplay") or "").strip()
        nom = re.sub(r"^IAD France\b", "iad", nom, flags=re.I)
        lieu = " ".join(x for x in [(c.get("address") or {}).get("postalCode"), (c.get("address") or {}).get("city")] if x)
        tel = c.get("phoneToDisplay") or ""
        tel = " ".join(tel[i:i + 2] for i in range(0, len(tel), 2)) if tel.isdigit() else tel
        return {"nom": nom or None, "contact": " · ".join(x for x in [lieu, tel] if x) or None}

    def enregistrer(self):
        CACHE.write_text(json.dumps(self.fiches, ensure_ascii=False, indent=0), encoding="utf-8")


def lire(a, type_):
    prix = a.get("price")
    if isinstance(prix, list):
        prix = prix[0]
    photos = a.get("photos") or []
    return {
        "source": NOM,
        "source_id": a["id"],
        "url": f"https://www.bienici.com/annonce/{a['id']}",
        "type": type_,
        "titre": a.get("title") or f"Maison {a.get('roomsQuantity') or ''} pièces",
        "prix": int(prix) if prix else None,
        "surface": a.get("surfaceArea"),
        "pieces": a.get("roomsQuantity"),
        "chambres": a.get("bedroomsQuantity"),
        "terrain": int(a["landSurfaceArea"]) if a.get("landSurfaceArea") else None,
        "commune": a.get("city"),
        "code_postal": a.get("postalCode"),
        "insee": (a.get("district") or {}).get("insee_code"),
        "agence": None,  # rempli par Agences.vendeur
        "agence_contact": None,
        "dpe": a.get("energyClassification") if a.get("energyClassification") in list("ABCDEFG") else None,
        "photo": photos[0].get("url") if photos else None,
        "description": (a.get("description") or "")[:600],
    }
