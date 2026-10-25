"""Outils partagés par les collecteurs : téléchargement poli et lecture des nombres."""
import re
import threading
import time
from urllib.parse import urlsplit

import requests

ENTETES = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
PAUSE_S = 1.5  # entre deux pages d'un même site, pour ne pas le surcharger
PAUSES = {"www.seloger.com": 4}  # sites qui bloquent quand on va trop vite

# Les sites sont collectés en parallèle : une session par fil, une pause par site.
_local = threading.local()
_verrou = threading.Lock()
_dernier_appel = {}


def _session():
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
        _local.session.headers.update(ENTETES)
    return _local.session


def _patienter(url):
    hote = urlsplit(url).netloc
    with _verrou:
        prochain = max(time.monotonic(), _dernier_appel.get(hote, 0) + PAUSES.get(hote, PAUSE_S))
        _dernier_appel[hote] = prochain
    time.sleep(max(0, prochain - time.monotonic()))


def telecharger(url, entetes=None):
    """Renvoie (url_finale, html) ou (None, None) si la page n'existe pas."""
    _patienter(url)
    try:
        r = _session().get(url, timeout=30, headers=entetes)
    except requests.RequestException:
        time.sleep(10)  # coupure passagère : un second essai avant d'abandonner
        r = _session().get(url, timeout=30, headers=entetes)
    if r.status_code >= 500:  # panne passagère du site : un second essai, puis on saute cette page
        time.sleep(10)
        r = _session().get(url, timeout=30, headers=entetes)
        if r.status_code >= 500:
            return None, None
    if r.status_code in (404, 410):
        return None, None
    r.raise_for_status()
    return r.url, r.text


def nombre(texte):
    """'139 000' -> 139000 ; '1 225,5' -> 1225.5 ; None si vide."""
    if texte is None:
        return None
    t = re.sub(r"[\s \xa0 ]", "", str(texte)).replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return int(v) if v.is_integer() else v


def chercher(motif, texte, groupe=1):
    m = re.search(motif, texte, re.I)
    return m.group(groupe) if m else None


CHIFFRES = r"(\d[\d\s \xa0 ]*(?:[.,]\d+)?)"


def terrain(texte):
    """Surface du terrain en m² : « terrain de 1 200 m² », « 2 500 m² de terrain », « 1,5 ha de terrain »."""
    for motif, facteur in (
        (r"(?:terrain|parcelle|jardin)\s*(?:clos\s*)?(?:arbor[ée]\s*)?(?:de|d'environ|d’environ|:)?\s*" + CHIFFRES + r"\s*m(?:²|2)\b", 1),
        (CHIFFRES + r"\s*m(?:²|2)\s*de\s*(?:terrain|parcelle)", 1),
        (r"(?:terrain|parcelle)\s*(?:de|d'environ|d’environ|:)?\s*" + CHIFFRES + r"\s*(?:ha|hectares?)\b", 10000),
        (CHIFFRES + r"\s*(?:ha|hectares?)\s*(?:de\s*)?(?:terrain|parcelle|prairie|pr[ée]s|bois)", 10000),
    ):
        v = nombre(chercher(motif, texte))
        if v:
            return int(v * facteur)
    return None


def caracteristiques(texte):
    """Extrait pièces, chambres et terrain d'un texte d'annonce."""
    return {
        "pieces": nombre(chercher(r"(\d+)\s*pi[eè]ces?\b", texte)),
        "chambres": nombre(chercher(r"(\d+)\s*\|?\s*chambres?\b", texte)),
        "terrain": terrain(texte),
    }
