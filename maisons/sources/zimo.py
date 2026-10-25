"""Zimo.fr : regroupe agences et particuliers, dont des annonces de particuliers reprises de Leboncoin."""
import re

from bs4 import BeautifulSoup

from ..communes import CENTRES, Repertoire, slug
from .commun import caracteristiques, chercher, nombre, telecharger

NOM = "Zimo"
BASE = "https://www.zimo.fr"
CHEMINS = {"vente": "vente", "location": "location"}
PAGES_MAX = 10

_rep = None


def commune_du_titre(titre):
    """'Vente Maison de ville Argenton-sur-Creuse (36) 5 pièces' -> 'Argenton-sur-Creuse'.
    Le type de bien précède le nom : on essaie les derniers mots, du plus court au plus long."""
    global _rep
    _rep = _rep or Repertoire()
    m = re.search(r"^(.*?)\s*\(\d{2}\)", titre)
    if not m:
        return None
    mots = m.group(1).split()
    for k in range(1, min(6, len(mots)) + 1):
        candidat = " ".join(mots[-k:])
        if _rep.trouver(candidat):
            return candidat
    return mots[-1] if mots else None  # hors rayon : sera écartée par la collecte


def collecter(communes, journal=print):
    # La page d'un centre liste d'abord les biens les plus proches : on avance tant qu'elle en montre dans les secteurs.
    global _rep
    _rep = _rep or Repertoire()
    vues = {}
    for centre in CENTRES.values():
        lieu = f"{slug(centre['nom'])}-{centre['code_postal']}"
        for type_, chemin in CHEMINS.items():
            for page in range(1, PAGES_MAX + 1):
                url = f"{BASE}/annonces/immobilier/{chemin}/maison/{lieu}" + (f"?page={page}" if page > 1 else "")
                _, html = telecharger(url)
                if html is None:
                    break
                annonces = lire_page(html, type_)
                dans_rayon = [a for a in annonces if _rep.trouver(a["commune"])]
                for a in annonces:
                    vues[a["source_id"]] = a
                if not dans_rayon:
                    break
            journal(f"  {NOM} {type_:8} {lieu:30} total {len(vues)}")
    return list(vues.values())


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for art in soup.find_all("article"):
        lien = art.find("a", href=re.compile(r"^(/|https://www\.zimo\.fr/)annonce"))
        if not lien:
            continue
        a = lire_carte(art, lien["href"], type_)
        if a:
            annonces.append(a)
    return annonces


def lire_carte(art, href, type_):
    jetons = [t.strip() for t in art.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)
    titre = next((t for t in jetons if re.match(r"^(Vente|Location)\b", t) and re.search(r"\(\d{2}\)", t)), None)
    if not titre or "neuf" in titre.lower() or "à construire" in texte.lower():
        return None
    vendeur = next((t for t in jetons if t in ("Particulier", "Pro")), None)
    origine = chercher(r"m²\s*\|\s*([^|]+?)\s*\|\s*il y a", texte)
    agence = "Particulier" if vendeur == "Particulier" else (origine or "Professionnel")
    if vendeur == "Particulier" and origine:
        agence += f" ({origine})"
    img = art.find("img")
    url = href if href.startswith("http") else BASE + href
    return {
        "source": NOM,
        "source_id": url.rstrip("/").rsplit("/", 1)[-1],
        "url": url,
        "type": type_,
        "titre": re.sub(r"^(Vente|Location)\s+", "", titre),
        "prix": nombre(chercher(r"(\d[\d\s \xa0]*)\s*€", texte)),
        "surface": nombre(chercher(r"(\d+(?:[.,]\d+)?)\s*m²", titre)),
        **caracteristiques(texte),
        "commune": commune_du_titre(titre),
        "code_postal": None,
        "agence": agence,
        "dpe": chercher(r"\bDPE\s*:?\s*\|?\s*([A-G])\b", texte),
        "photo": img.get("src") if img and img.get("src", "").startswith("http") else None,
        "description": max(jetons, key=len)[:600],
    }
