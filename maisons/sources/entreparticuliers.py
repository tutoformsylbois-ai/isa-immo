"""Entreparticuliers.com : surtout des particuliers, mais aussi des professionnels (non distingués sur la liste).
La page d'une commune montre aussi des biens des communes proches."""
import re

from bs4 import BeautifulSoup

from ..communes import slug
from .commun import caracteristiques, chercher, nombre, telecharger

NOM = "Entreparticuliers"
BASE = "https://www.entreparticuliers.com"
PAGES_MAX = 5


def collecter(communes, journal=print):
    vues = {}
    for c in communes:
        if not c.get("code_postal"):
            continue
        for type_ in ("vente", "location"):
            url = f"{BASE}/annonces-immobilieres/{type_}/maison/{slug(c['nom'])}-{c['code_postal']}"
            for page in range(1, PAGES_MAX + 1):
                _, html = telecharger(url if page == 1 else f"{url}?page={page}")
                if html is None:
                    break
                lues = lire_page(html, type_)
                nouvelles = [a for a in lues if a["source_id"] not in vues]
                for a in lues:
                    vues[a["source_id"]] = a
                if not nouvelles or f"?page={page + 1}" not in html:
                    break
        journal(f"  {NOM} {c['nom']:35} total {len(vues)}")
    return list(vues.values())


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for art in soup.find_all("article"):
        lien = art.find("a", href=re.compile(rf"^/annonces-immobilieres/maison/{type_}/.+/ref-\d+$"))
        if lien:  # les « demandes » (particuliers qui cherchent un bien) n'ont pas ce lien
            annonces.append(lire_carte(art, lien["href"], type_))
    return annonces


def lire_carte(art, href, type_):
    jetons = [t.strip() for t in art.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)
    titre = next((t for t in jetons if re.match(r"^Maison (à vendre|à louer)", t)), "Maison")
    img = art.find("img")
    src = (img.get("src") or "") if img else ""
    return {
        "source": NOM,
        "source_id": chercher(r"/ref-(\d+)$", href),
        "url": BASE + href,
        "type": type_,
        "titre": titre,
        "prix": nombre(chercher(r"(\d[\d\s \xa0]*)\s*€", texte)),
        "surface": nombre(chercher(r"(\d+(?:[.,]\d+)?)\s*m²", titre)),
        **caracteristiques(texte),
        "commune": chercher(r"\|\s*([^|]+?)\s*\(\d{2}\)\s*\|", texte),
        "code_postal": chercher(r"-(\d{5})/", href),
        "agence": None,
        "dpe": None,
        "photo": (BASE + src) if src.startswith("/") and "epc-photos" in src else None,
        "description": texte[:600],
    }
