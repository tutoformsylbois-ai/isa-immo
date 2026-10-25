"""Lesiteimmo.com : regroupe les annonces des agences, réseaux (iad, SAFTI…) et notaires."""
import re

from bs4 import BeautifulSoup

from .commun import caracteristiques, chercher, nombre, telecharger

NOM = "Lesiteimmo"
BASE = "https://www.lesiteimmo.com"
CHEMINS = {"vente": "acheter", "location": "louer"}
PAGES_MAX = 10


def urls_a_visiter(communes):
    for c in communes:
        if not c.get("code_postal"):
            continue
        for type_, chemin in CHEMINS.items():
            yield type_, f"{BASE}/{chemin}/maison/{_slug(c['nom'])}-{c['code_postal']}"


def _slug(nom):
    from ..communes import slug
    return slug(nom)


def collecter(communes, journal=print):
    vues = {}
    for type_, url in urls_a_visiter(communes):
        for page in range(1, PAGES_MAX + 1):
            url_page = url if page == 1 else f"{url}?page={page}"
            url_finale, html = telecharger(url_page)
            if html is None:
                break
            annonces = lire_page(html, type_)
            nouvelles = [a for a in annonces if a["source_id"] not in vues]
            for a in annonces:
                vues[a["source_id"]] = a
            if not nouvelles or f"page={page + 1}" not in html:
                break
        journal(f"  {NOM} {type_:8} {url.rsplit('/', 1)[-1]:40} total {len(vues)}")
    return list(vues.values())


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for article in soup.find_all("article"):
        lien = article.find("a", href=re.compile(r"^/(acheter|louer)/maison[^/]*/[^/]+/\d+$"))
        if not lien:
            continue
        a = lire_carte(article, lien["href"], type_)
        if a:
            annonces.append(a)
    return annonces


def lire_carte(article, href, type_):
    jetons = [t.strip() for t in article.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)

    i_type = next((i for i, t in enumerate(jetons) if re.match(r"^\w+ à (vendre|louer)$", t)), None)
    if i_type is None:
        return None
    agence = None
    for t in reversed(jetons[:i_type]):
        if t != "Partenaire":
            if not re.match(r"^(\+?\d+(/\d+)?|[A-G])$", t):
                agence = t
            break
    titre = jetons[i_type + 1] if i_type + 1 < len(jetons) else None

    prix = None
    for t in jetons[i_type + 2:i_type + 5]:
        if "€" in t:
            prix = nombre(t.replace("€", ""))
            break

    surface = None
    commune = code_postal = None
    for i, t in enumerate(jetons):
        if surface is None and re.match(r"^\d[\d\s,.]*\s*m²$", t):
            surface = nombre(t.replace("m²", ""))
        m = re.match(r"^\((\d{5})\)$", t)
        if m and commune is None and i > 0:
            commune, code_postal = jetons[i - 1], m.group(1)

    # Les cartes ont une ligne « 4 pièces • 2 chambres • 75 m² », plus fiable que le titre.
    carac = caracteristiques(texte)
    for t in jetons[i_type + 2:]:
        if m := re.match(r"^(\d+) pièces?$", t):
            carac["pieces"] = int(m.group(1))
            break

    img = article.find("img")
    description = max(jetons, key=len) if jetons else ""
    return {
        "source": NOM,
        "source_id": href.rsplit("/", 1)[-1],
        "url": BASE + href,
        "type": type_,
        "titre": titre,
        "prix": prix,
        "surface": surface,
        **carac,
        "commune": commune,
        "code_postal": code_postal,
        "agence": agence,
        "dpe": jetons[0] if re.match(r"^[A-G]$", jetons[0]) else chercher(r"\|\s*([A-G])\s*\|\s*1/\d+", texte),
        "photo": img.get("src") if img else None,
        "description": description[:600],
    }
