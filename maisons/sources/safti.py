"""SAFTI : réseau de mandataires. La page d'une commune montre aussi des biens des communes proches."""
import re

from bs4 import BeautifulSoup

from ..communes import slug
from .commun import chercher, nombre, telecharger

NOM = "SAFTI"
BASE = "https://www.safti.fr"
CHEMINS = {"vente": "achat", "location": "location"}


def collecter(communes, journal=print):
    vues = {}
    for c in communes:
        if not c.get("code_postal"):
            continue
        for type_, chemin in CHEMINS.items():
            _, html = telecharger(f"{BASE}/annonces/{chemin}/maison/{slug(c['nom'])}-{c['code_postal']}")
            if html is None:
                continue
            for a in lire_page(html, type_, chemin):
                vues[a["source_id"]] = a
        journal(f"  {NOM} {c['nom']:35} total {len(vues)}")
    return list(vues.values())


def lire_page(html, type_, chemin):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for art in soup.find_all("article"):
        lien = art.find("a", href=re.compile(rf"^/annonces/{chemin}/maison/[^/]+/\d+$"))
        if lien:
            annonces.append(lire_carte(art, lien["href"], type_))
    return annonces


def lire_carte(art, href, type_):
    jetons = [t.strip() for t in art.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)
    titre = next((t for t in jetons if t.startswith("Maison")), "Maison")
    i_cp = next((i for i, t in enumerate(jetons) if re.fullmatch(r"\d{5}", t)), None)
    commune = jetons[i_cp - 2] if i_cp and i_cp >= 2 and jetons[i_cp - 1] == "(" else None
    # La première image est souvent la photo du conseiller : on prend celle du bien si elle existe.
    photos = [i.get("src") for i in art.find_all("img") if (i.get("src") or "").startswith("http")]
    photo = next((p for p in photos if "agent-photo" not in p), None)
    return {
        "source": NOM,
        "source_id": href.rsplit("/", 1)[-1],
        "url": BASE + href,
        "type": type_,
        "titre": titre,
        "prix": nombre(chercher(r"(\d[\d\s \xa0]*)\s*€", texte)),
        "surface": nombre(chercher(r"(\d+(?:[.,]\d+)?)\s*m²", titre)),
        "pieces": nombre(chercher(r"(\d+)\s*pièces?", titre)),
        "chambres": nombre(chercher(r"bedroom\s*\|\s*(\d+)", texte)),
        "terrain": nombre(chercher(r"Terrain\s*\|\s*(\d[\d\s \xa0]*)\s*m²", texte)),
        "commune": commune,
        "code_postal": jetons[i_cp] if i_cp is not None else None,
        "agence": "SAFTI",
        "dpe": None,
        "photo": photo,
        "description": texte[:600],
    }
