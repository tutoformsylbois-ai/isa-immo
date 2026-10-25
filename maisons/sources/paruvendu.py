"""ParuVendu.fr : annonces d'agences et de particuliers."""
import re

from bs4 import BeautifulSoup

from .commun import caracteristiques, chercher, nombre, telecharger

NOM = "ParuVendu"
BASE = "https://www.paruvendu.fr"
PAGES_MAX = 10


def urls_a_visiter(communes):
    from ..communes import slug
    for c in communes:
        if not c.get("code_postal"):
            continue
        for type_ in ("vente", "location"):
            yield type_, f"{BASE}/immobilier/{type_}/maison/{slug(c['nom'])}-{c['code_postal']}/"


def collecter(communes, journal=print):
    vues = {}
    deja = set()  # les petites communes redirigent souvent vers la même page départementale
    for type_, url in urls_a_visiter(communes):
        url_page = url
        for page in range(1, PAGES_MAX + 1):
            url_finale, html = telecharger(url_page)
            if html is None or (url_finale in deja):
                break
            deja.add(url_finale)
            for a in lire_page(html, type_):
                vues[a["source_id"]] = a
            suivante = page_suivante(html, page)
            if not suivante:
                break
            url_page = suivante
        journal(f"  {NOM} {type_:8} {url.rstrip('/').rsplit('/', 1)[-1]:40} total {len(vues)}")
    return list(vues.values())


def page_suivante(html, page):
    soup = BeautifulSoup(html, "html.parser")
    lien = soup.find("a", attrs={"rel": "next"}) or soup.find("a", href=re.compile(rf"[?&]p={page + 1}\b"))
    if not lien:
        return None
    href = lien["href"]
    return href if href.startswith("http") else BASE + href


def lire_page(html, type_):
    soup = BeautifulSoup(html, "html.parser")
    annonces = []
    for bloc in soup.select("div.blocAnnonce[data-id]"):
        lien = bloc.find("a", href=re.compile(rf"^/immobilier/{type_}/maison/\d"))
        if not lien:
            continue
        annonces.append(lire_carte(bloc, lien["href"], type_))
    return annonces


def lire_carte(bloc, href, type_):
    jetons = [t.strip() for t in bloc.get_text("|", strip=True).split("|") if t.strip()]
    texte = " | ".join(jetons)

    prix = nombre(chercher(r"(\d[\d\s \xa0]*)\s*€", texte))
    surface = nombre(chercher(r"(?:Maison|Villa)\s*(\d[\d\s,.]*)\s*m\b", texte))
    commune = None
    for t in jetons:
        m = re.match(r"^(.+?)\s*\((\d{2})\)$", t)
        if m:
            commune = m.group(1)
            break

    description = max(jetons, key=len) if jetons else ""
    agence = None
    i_desc = jetons.index(description) if description else -1
    i_date = next((i for i, t in enumerate(jetons) if re.match(r"^\d{2}/\d{2}/\d{4}$", t)), None)
    if i_date is not None and i_desc < i_date:
        noms = [t for t in jetons[i_desc + 1:i_date]
                if not re.search(r"annonces$|^360$|^Visite 360", t)]
        agence = " – ".join(noms) or None

    photo = None
    for img in bloc.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if src.startswith("http") and "transparent" not in src:
            photo = src
            break

    return {
        "source": NOM,
        "source_id": bloc["data-id"],
        "url": BASE + href,
        "type": type_,
        "titre": chercher(r"^([^.]{10,90})\.", description, 1) or (description[:80] if description else None),
        "prix": prix,
        "surface": surface,
        **caracteristiques(texte),
        "commune": commune,
        "code_postal": None,
        "agence": agence,
        "dpe": chercher(r"DPE\s*:\s*\|\s*([A-G])\b", texte),
        "photo": photo,
        "description": description[:600],
    }
