"""iad France : premier réseau de mandataires. La page d'une commune montre aussi des biens des communes proches."""
import re

from bs4 import BeautifulSoup

from ..communes import slug
from .commun import chercher, nombre, telecharger

NOM = "iad"
BASE = "https://www.iadfrance.fr"
CHEMINS = {"vente": "vente", "location": "location"}


def collecter(communes, journal=print):
    vues = {}
    for c in communes:
        if not c.get("code_postal"):
            continue
        for type_, chemin in CHEMINS.items():
            _, html = telecharger(f"{BASE}/annonces/{slug(c['nom'])}-{c['code_postal']}/{chemin}/maison")
            if html is None:
                continue
            for a in lire_page(html, type_):
                vues[a["source_id"]] = a
        journal(f"  {NOM} {c['nom']:35} total {len(vues)}")
    return list(vues.values())


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for art in soup.find_all("article"):
        lien = art.find("a", href=re.compile(r"^/annonce/maison-"))
        if lien:
            annonces.append(lire_carte(art, lien["href"], type_))
    return annonces


def lire_carte(art, href, type_):
    jetons = [t.strip() for t in art.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)
    titre = next((t for t in jetons if re.search(r" à .+\(\d{5}\)$", t)), "")
    commune = chercher(r" à (.+?)\s*\(\d{5}\)$", titre)
    i_voir = max((i for i, t in enumerate(jetons) if t == "Voir plus"), default=None)
    img = art.find("img")
    return {
        "source": NOM,
        "source_id": chercher(r"/r(\d+)$", href) or href,
        "url": BASE + href,
        "type": type_,
        "titre": titre or "Maison",
        "prix": nombre(chercher(r"(\d[\d\s \xa0]*)\s*€", texte)),
        "surface": nombre(chercher(r"\|\s*(\d[\d\s \xa0,.]*)\s*m²\s*(?:\||$)", texte)),
        "pieces": nombre(chercher(r"(\d+)\s*pièces?", texte)),
        "chambres": nombre(chercher(r"(\d+)\s*chambres?", texte)),
        "terrain": nombre(chercher(r"(\d[\d\s \xa0]*)\s*m²\s*de terrain", texte)),
        "commune": commune,
        "code_postal": chercher(r"\((\d{5})\)$", titre),
        # Le nom du conseiller suit « Voir plus ».
        "agence": f"iad – {jetons[i_voir + 1]}" if i_voir is not None and i_voir + 1 < len(jetons) else "iad",
        "dpe": None,
        "photo": img.get("src") if img and (img.get("src") or "").startswith("http") else None,
        "description": texte[:600],
    }
