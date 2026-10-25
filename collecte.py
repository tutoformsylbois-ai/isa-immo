"""Collecte les annonces de maisons (vente et location) dans les secteurs suivis
(Argenton et 30 km alentour, 10 km autour d'Azerables, 10 km autour de Liglet).

À lancer une fois par jour (lancer_collecte.bat le fait) :  py collecte.py
Les sites sont interrogés en parallèle, chacun à son rythme (une page toutes les 1,5 s au plus).
"""
import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from maisons import base
from maisons.communes import Repertoire
from maisons.sources import SOURCES
from maisons.sources.commun import terrain


def collecter(journal=print):
    rep = Repertoire()
    cx = base.connexion()
    debut = base.maintenant()
    collecte_id = cx.execute("INSERT INTO collectes (debut) VALUES (?)", (debut,)).lastrowid
    cx.commit()

    bilan = {}
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        taches = {pool.submit(source.collecter, rep.communes, journal=journal): source for source in SOURCES}
        # La base n'est écrite que depuis ce fil, au fur et à mesure que les sites terminent.
        for tache in as_completed(taches):
            source = taches[tache]
            compte = {"lues": 0, "hors_zone": 0, "nouvelle": 0, "baisse": 0, "hausse": 0, "retirees": 0}
            try:
                annonces = tache.result()
            except Exception as e:  # une source en panne ne doit pas bloquer les autres
                journal(f"!! {source.NOM} : {e}")
                traceback.print_exc()
                bilan[source.NOM] = {"erreur": str(e)}
                continue
            for a in annonces:
                compte["lues"] += 1
                commune = rep.trouver(a["commune"], a.get("code_postal"), a.get("insee"))
                if commune is None:
                    compte["hors_zone"] += 1
                    continue
                if not a.get("terrain"):
                    a["terrain"] = terrain(f"{a.get('titre') or ''} {a.get('description') or ''}")
                evenement = base.enregistrer(cx, a, commune, rep.zone(commune), base.maintenant())
                if evenement:
                    compte[evenement] += 1
            # Si un site renvoie soudain beaucoup moins d'annonces (blocage, page changée), on ne retire rien.
            actives = cx.execute("SELECT COUNT(*) FROM annonces WHERE source=? AND active=1", (source.NOM,)).fetchone()[0]
            if compte["lues"] - compte["hors_zone"] < 0.5 * actives:
                journal(f"!! {source.NOM} : seulement {compte['lues'] - compte['hors_zone']} annonces pour {actives} connues, "
                        "aucune n'est marquée comme retirée")
            else:
                compte["retirees"] = base.desactiver_absentes(cx, source.NOM, debut)
            cx.commit()
            bilan[source.NOM] = compte
            journal(f"{source.NOM} : {compte}")

    cx.execute("UPDATE collectes SET fin=?, bilan=? WHERE id=?",
               (base.maintenant(), json.dumps(bilan, ensure_ascii=False), collecte_id))
    cx.commit()
    cx.close()
    return bilan


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    collecter()
