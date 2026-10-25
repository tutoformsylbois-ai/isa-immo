"""PAP.fr : annonces de particuliers uniquement. La page d'une commune montre aussi les communes proches."""
import re

from bs4 import BeautifulSoup

from .commun import caracteristiques, chercher, nombre, telecharger

NOM = "PAP"
BASE = "https://www.pap.fr"
# Identifiants géographiques PAP des centres des secteurs (relevés une fois sur pap.fr).
LIEUX = ["argenton-sur-creuse-36200-g21163", "azerables-23160-g15280", "liglet-86290-g41620"]
PAGES = {"vente": "/annonce/vente-maisons-{lieu}", "location": "/annonce/locations-maison-{lieu}"}


def collecter(communes, journal=print):
    vues = {}
    for lieu in LIEUX:
        for type_, chemin in PAGES.items():
            _, html = telecharger(BASE + chemin.format(lieu=lieu))
            if html is None:
                continue
            lues = lire_page(html, type_)
            for a in lues:
                vues[a["source_id"]] = a
            journal(f"  {NOM} {type_:8} {lieu:35} {len(lues)} annonces")
    return list(vues.values())


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for carte in soup.select(".search-list-item-alt, .search-list-item"):
        lien = carte.find("a", href=re.compile(r"^/annonces/"))
        if not lien:
            continue
        a = lire_carte(carte, lien["href"], type_)
        if a:
            annonces.append(a)
    return annonces


def lire_carte(carte, href, type_):
    jetons = [t.strip() for t in carte.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)
    if "à construire" in texte.lower():
        return None
    commune = code_postal = None
    for t in jetons:
        if m := re.match(r"^(.+?)\s*\((\d{5})\)\.?$", t):
            commune, code_postal = m.group(1), m.group(2)
            commune = re.sub(r"^Maison .*?m²\s*", "", commune)
            break
    img = carte.find("img")
    return {
        "source": NOM,
        "source_id": chercher(r"-r(\d+)", href) or href.rsplit("/", 1)[-1],
        "url": BASE + href,
        "type": type_,
        "titre": next((t for t in jetons if t.startswith("**") or len(t) > 40), "Maison de particulier").strip("* ")[:120],
        "prix": nombre((chercher(r"([\d.\s \xa0]+)\s*€", texte) or "").replace(".", "")),
        "surface": nombre(chercher(r"\|\s*(\d+(?:[.,]\d+)?)\s*m²", texte)),
        **caracteristiques(texte),
        "commune": commune,
        "code_postal": code_postal,
        "agence": "Particulier",
        "dpe": None,
        "photo": (img.get("data-src") or img.get("src")) if img else None,
        "description": max(jetons, key=len)[:600],
    }
