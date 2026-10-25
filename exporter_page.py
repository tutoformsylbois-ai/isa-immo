"""Fabrique la page des annonces à partir de la base.

  py exporter_page.py             -> publication/isa-immo.html (claude.ai : vignettes intégrées)
  py exporter_page.py --netlify   -> site/index.html (Netlify : photos chargées depuis les sites d'annonces)
L'application locale (app.py) fabrique la même page à la volée.
"""
import base64
import hashlib
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import requests

from maisons import base, requetes
from maisons.communes import CENTRES, LIBELLES_ZONES, Repertoire
from maisons.sources import CONTENU, EXCLUS, SOURCES
from maisons.sources.commun import ENTETES

RACINE = Path(__file__).resolve().parent
PUBLICATION = RACINE / "publication"
MODELE = PUBLICATION / "modele.html"
CACHE = RACINE / "data" / "vignettes"
MARQUE_DONNEES = "/*__DONNEES__*/null"
MARQUE_MAJ = "/*__MAJ__*/"
MAJ = {"claude": "maj_claude.js", "netlify": "maj_netlify.js", "local": "maj_local.js"}

# claude.ai ajoute lui-même le squelette du document ; sur Netlify et en local, la page doit l'avoir.
SQUELETTE = (
    '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    "<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n"
    "{page}\n</body></html>\n"
)

RESEAUX_MANDATAIRES = ("iad", "safti", "capifrance", "optimhome", "megagence", "proprietes-privees", "propriétés privées",
                       "efficity", "bsk", "3g immo", "lafourmi", "dr house", "expertimo", "sextant", "selectimmo",
                       "mandataire", "conseiller indépendant", "agent commercial")
RESEAUX_SEULS = {"safti", "iad", "optimhome", "proprietes privees", "megagence", "capifrance", "efficity", "bsk"}


def url_vignette(url):
    """Demande au site une petite version de la photo."""
    return url.replace("w=768&h=576&q=70", "w=320&h=240&q=60")


def vignette_integree(url):
    if not url:
        return None
    fichier = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if not fichier.exists():
        try:
            r = requests.get(url_vignette(url), headers=ENTETES, timeout=30)
            r.raise_for_status()
            fichier.write_bytes(r.content)
        except requests.RequestException:
            return None
    return "data:image/jpeg;base64," + base64.b64encode(fichier.read_bytes()).decode()


def nom_vendeur(agence, source):
    """Nom lisible et identique d'un site à l'autre : 'iad France  Justin Lavigne' -> 'iad – Justin Lavigne'."""
    if not agence:
        return None
    n = re.sub(r"\s+", " ", agence).strip()
    n = re.sub(r"^iad France\s*[-–]?\s*", "iad – ", n, flags=re.I)
    n = re.sub(r"^SAFTI\s*[-–]?\s*(.+?)\s*conseiller indépendant$", r"SAFTI – \1", n, flags=re.I)
    return n.rstrip(" –")


def cle_vendeur(nom):
    """Même clé pour 'IMMO RESEAU' et 'Immo Réseau'."""
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFD", nom.lower()).encode("ascii", "ignore").decode()).strip()


def categorie(agence, source):
    a = (agence or "").lower()
    if a.startswith("particulier") or source == "PAP":
        return "particulier"
    if source == "Notaires" or re.search(r"notair|notari|^(ma[iî]tre|me|scp|selarl|office)\b", a):
        return "notaire"
    if any(r in a for r in RESEAUX_MANDATAIRES):
        return "mandataire"
    return "agence" if agence and a not in ("professionnel", "agence") else "inconnu"


def compact(b, rep):
    commune = rep.trouver(None, insee=b["insee"]) or {}
    vendeurs = []
    for s in b["sources"]:
        nom = nom_vendeur(s["agence"], s["source"])
        vendeurs.append({"nom": nom, "categorie": categorie(nom, s["source"])})
    cats = {v["categorie"] for v in vendeurs}
    return {
        "ids": b["ids"], "type": b["type"], "zones": (b["zone"] or "").split(","), "titre": b["titre"], "prix": b["prix"],
        "surface": b["surface"], "pieces": b["pieces"], "chambres": b["chambres"], "terrain": b["terrain"],
        "commune": b["commune"], "km": b["distance_km"], "dist": commune.get("distances"),
        "agence": nom_vendeur(b["agence"], b["source"]), "dpe": b["dpe"],
        "vu": b["premiere_vue"], "variation": b["variation"],
        "sources": [{"source": s["source"], "url": s["url"]} for s in b["sources"]],
        "vendeurs": vendeurs,
        # Un bien vendu à la fois par un particulier et une agence compte dans les deux.
        "categories": sorted(cats - {"inconnu"}) or ["inconnu"],
        "particulier": "particulier" in cats,
        "photo": b["photo"],
    }


def annuaire(cx):
    """Tous les vendeurs professionnels vus dans les annonces actives, avec leurs coordonnées quand un site les donne."""
    vendeurs = {}
    for l in cx.execute("SELECT source, agence, agence_contact, type, commune FROM annonces WHERE active=1"):
        nom = nom_vendeur(l["agence"], l["source"])
        cat = categorie(nom, l["source"])
        if cat in ("particulier", "inconnu"):
            continue
        v = vendeurs.setdefault(cle_vendeur(nom), {"nom": nom, "categorie": cat, "vente": 0, "location": 0,
                                                    "sources": set(), "communes": set(), "contact": None})
        v[l["type"]] += 1
        v["sources"].add(l["source"])
        v["communes"].add(l["commune"])
        # Pour un réseau sans nom de conseiller, les coordonnées seraient celles d'un conseiller pris au hasard.
        if cle_vendeur(nom) not in RESEAUX_SEULS:
            v["contact"] = v["contact"] or l["agence_contact"]
    liste = sorted(vendeurs.values(), key=lambda v: (-(v["vente"] + v["location"]), v["nom"].lower()))
    for v in liste:
        v["sources"], v["communes"] = sorted(v["sources"]), sorted(v["communes"])
    return liste


def donnees():
    rep = Repertoire()
    cx = base.connexion()
    biens = [compact(b, rep) for b in requetes.annonces_actives(cx)]
    collectes = [r["debut"] for r in cx.execute(
        "SELECT debut FROM collectes WHERE fin IS NOT NULL ORDER BY debut DESC LIMIT 2")]
    il_y_a_30j = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    retirees = [dict(r) for r in cx.execute(
        "SELECT type, commune, prix, titre, derniere_vue AS vu FROM annonces WHERE active=0 AND derniere_vue >= ?",
        (il_y_a_30j,))]
    derniere = requetes.derniere_collecte(cx)
    bilan = json.loads(derniere["bilan"]) if derniere and derniere["bilan"] else {}
    vendeurs = annuaire(cx)
    particuliers = cx.execute(
        "SELECT COUNT(*) FROM annonces WHERE active=1 AND (agence LIKE 'Particulier%' OR source='PAP')").fetchone()[0]
    cx.close()
    return {
        "maj": derniere["fin"] if derniere else None,
        # « Nouveau » = vu pour la première fois pendant la dernière collecte (s'il y en a eu une avant).
        "precedente": collectes[0] if len(collectes) == 2 else None,
        "zones": LIBELLES_ZONES,
        "centres": {k: c["nom"] for k, c in CENTRES.items()},
        "annonces": biens,
        "retirees": retirees,
        "annuaire": vendeurs,
        "particuliers": particuliers,
        "sources": [{"nom": s.NOM, "contenu": CONTENU.get(s.NOM, ""), "bilan": bilan.get(s.NOM)} for s in SOURCES],
        "exclus": [{"nom": n, "raison": r} for n, r in EXCLUS.items()],
    }


def page(mode):
    """mode : 'claude', 'netlify' ou 'local'."""
    d = donnees()
    if mode == "claude":
        CACHE.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for b, data in zip(d["annonces"], pool.map(lambda b: vignette_integree(b["photo"]), d["annonces"])):
                b["photo"] = data
    else:
        for b in d["annonces"]:
            b["photo"] = url_vignette(b["photo"]) if b["photo"] else None
    json_txt = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (MODELE.read_text(encoding="utf-8")
            .replace(MARQUE_DONNEES, json_txt)
            .replace(MARQUE_MAJ, (PUBLICATION / MAJ[mode]).read_text(encoding="utf-8")))
    return (html if mode == "claude" else SQUELETTE.replace("{page}", html)), d


def main(mode):
    html, d = page(mode)
    sortie = RACINE / "site" / "index.html" if mode == "netlify" else PUBLICATION / "isa-immo.html"
    sortie.parent.mkdir(exist_ok=True)
    sortie.write_text(html, encoding="utf-8")
    sans_photo = sum(1 for b in d["annonces"] if not b["photo"])
    print(f"{len(d['annonces'])} biens, {sans_photo} sans photo, {len(d['annuaire'])} vendeurs pros, "
          f"{sortie.stat().st_size / 1e6:.1f} Mo -> {sortie}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("netlify" if "--netlify" in sys.argv else "claude")
