"""Lecture des annonces pour la page : regroupement des doublons et récapitulatif."""
from datetime import datetime, timedelta


def _grouper(lignes):
    """Fusionne les annonces d'un même bien publié sur plusieurs sites."""
    groupes = {}
    for l in lignes:
        cle = l["empreinte"] or f"seul-{l['id']}"
        groupes.setdefault(cle, []).append(dict(l))
    biens = []
    for annonces in groupes.values():
        annonces.sort(key=lambda a: a["premiere_vue"])
        bien = dict(annonces[0])
        bien["premiere_vue"] = annonces[0]["premiere_vue"]
        bien["sources"] = [{"id": a["id"], "source": a["source"], "url": a["url"], "prix": a["prix"],
                            "agence": a["agence"]} for a in annonces]
        bien["favori"] = int(any(a["favori"] for a in annonces))
        bien["ids"] = [a["id"] for a in annonces]
        for champ in ("chambres", "terrain", "dpe", "photo", "agence"):
            if not bien[champ]:
                bien[champ] = next((a[champ] for a in annonces if a[champ]), None)
        biens.append(bien)
    return biens


def annonces_actives(cx):
    lignes = cx.execute("SELECT * FROM annonces WHERE active=1").fetchall()
    biens = _grouper(lignes)
    baisses = _dernieres_variations(cx)
    for b in biens:
        b["variation"] = next((baisses[i] for i in b["ids"] if i in baisses), None)
    biens.sort(key=lambda b: b["premiere_vue"], reverse=True)
    return biens


def _dernieres_variations(cx):
    """{annonce_id: {'ancien', 'nouveau', 'date'}} pour la dernière variation de prix de chaque annonce."""
    variations = {}
    lignes = cx.execute("SELECT annonce_id, date, prix FROM prix ORDER BY annonce_id, date").fetchall()
    precedent = {}
    for l in lignes:
        avant = precedent.get(l["annonce_id"])
        if avant is not None and l["prix"] and avant != l["prix"]:
            variations[l["annonce_id"]] = {"ancien": avant, "nouveau": l["prix"], "date": l["date"]}
        precedent[l["annonce_id"]] = l["prix"]
    return variations


def date_depuis(cx, periode):
    """'collecte' = depuis le début de l'avant-dernière collecte terminée ; sinon un nombre de jours."""
    if periode == "collecte":
        lignes = cx.execute("SELECT debut FROM collectes WHERE fin IS NOT NULL ORDER BY debut DESC LIMIT 2").fetchall()
        if len(lignes) == 2:
            return lignes[0]["debut"]
        periode = "7"
    jours = int(periode) if str(periode).isdigit() else 7
    return (datetime.now() - timedelta(days=jours)).isoformat(timespec="seconds")


def recapitulatif(cx, periode="collecte"):
    depuis = date_depuis(cx, periode)
    biens = annonces_actives(cx)
    nouvelles = [b for b in biens if b["premiere_vue"] >= depuis]
    baisses = [b for b in biens if b["variation"] and b["variation"]["date"] >= depuis
               and b["variation"]["nouveau"] < b["variation"]["ancien"] and b not in nouvelles]
    retirees = cx.execute("SELECT COUNT(*) FROM annonces WHERE active=0 AND derniere_vue >= ?", (depuis,)).fetchone()[0]
    return {"depuis": depuis, "nouvelles": nouvelles, "baisses": baisses, "retirees": retirees}


def derniere_collecte(cx):
    l = cx.execute("SELECT * FROM collectes WHERE fin IS NOT NULL ORDER BY debut DESC LIMIT 1").fetchone()
    return dict(l) if l else None
