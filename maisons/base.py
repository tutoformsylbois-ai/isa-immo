"""Base SQLite des annonces : ajout, suivi des prix, annonces disparues."""
import sqlite3
from datetime import datetime
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "data" / "annonces.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS annonces (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    url           TEXT,
    type          TEXT NOT NULL,          -- vente | location
    zone          TEXT NOT NULL,          -- secteurs séparés par des virgules : argenton, r10, r20, r30, azerables, liglet
    titre         TEXT,
    prix          INTEGER,
    prix_initial  INTEGER,
    surface       REAL,
    pieces        INTEGER,
    chambres      INTEGER,
    terrain       INTEGER,
    commune       TEXT,
    insee         TEXT,
    distance_km   REAL,
    agence        TEXT,
    agence_contact TEXT,                  -- adresse / téléphone du vendeur quand le site les donne
    dpe           TEXT,
    photo         TEXT,
    description   TEXT,
    empreinte     TEXT,                   -- pour repérer le même bien sur deux sites
    premiere_vue  TEXT NOT NULL,
    derniere_vue  TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    favori        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (source, source_id)
);
CREATE TABLE IF NOT EXISTS prix (
    annonce_id INTEGER NOT NULL REFERENCES annonces(id),
    date       TEXT NOT NULL,
    prix       INTEGER
);
CREATE TABLE IF NOT EXISTS collectes (
    id       INTEGER PRIMARY KEY,
    debut    TEXT NOT NULL,
    fin      TEXT,
    bilan    TEXT
);
"""


def connexion():
    FICHIER.parent.mkdir(exist_ok=True)
    cx = sqlite3.connect(FICHIER)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA)
    return cx


def maintenant():
    return datetime.now().isoformat(timespec="seconds")


def empreinte(a, commune):
    """Même type, même commune, même surface et même nombre de pièces = probablement le même bien."""
    if not a.get("surface"):
        return None
    # Partie entière de la surface : 84,62 m² sur un site et 84 m² sur un autre restent le même bien.
    return f"{a['type']}|{commune['insee']}|{int(a['surface'])}|{a.get('pieces') or ''}"


def enregistrer(cx, a, commune, zone, quand):
    """Ajoute ou met à jour une annonce. Renvoie 'nouvelle', 'baisse', 'hausse' ou None."""
    ligne = cx.execute("SELECT id, prix, active FROM annonces WHERE source=? AND source_id=?",
                       (a["source"], a["source_id"])).fetchone()
    champs = {
        "url": a["url"], "type": a["type"], "zone": zone, "titre": a["titre"], "prix": a["prix"],
        "surface": a["surface"], "pieces": a["pieces"], "chambres": a["chambres"], "terrain": a["terrain"],
        "commune": commune["nom"], "insee": commune["insee"], "distance_km": commune["distance_km"],
        "agence": a["agence"], "agence_contact": a.get("agence_contact"), "dpe": a["dpe"], "photo": a["photo"], "description": a["description"],
        "empreinte": empreinte(a, commune),
    }
    if ligne is None:
        cx.execute(
            f"INSERT INTO annonces (source, source_id, prix_initial, premiere_vue, derniere_vue, {', '.join(champs)}) "
            f"VALUES (?, ?, ?, ?, ?, {', '.join('?' * len(champs))})",
            (a["source"], a["source_id"], a["prix"], quand, quand, *champs.values()),
        )
        annonce_id = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.execute("INSERT INTO prix VALUES (?, ?, ?)", (annonce_id, quand, a["prix"]))
        return "nouvelle"

    evenement = None
    if a["prix"] and ligne["prix"] and a["prix"] != ligne["prix"]:
        evenement = "baisse" if a["prix"] < ligne["prix"] else "hausse"
        cx.execute("INSERT INTO prix VALUES (?, ?, ?)", (ligne["id"], quand, a["prix"]))
    elif not ligne["active"]:
        evenement = "nouvelle"  # annonce réapparue
    cx.execute(
        f"UPDATE annonces SET {', '.join(f'{k}=?' for k in champs)}, derniere_vue=?, active=1 WHERE id=?",
        (*champs.values(), quand, ligne["id"]),
    )
    return evenement


def desactiver_absentes(cx, source, debut):
    """Annonces d'une source non revues pendant cette collecte = retirées du site."""
    return cx.execute("UPDATE annonces SET active=0 WHERE source=? AND active=1 AND derniere_vue < ?",
                      (source, debut)).rowcount
