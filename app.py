"""Page web locale : py app.py puis ouvrir http://localhost:5000
C'est la même page que la version en ligne, fabriquée à chaque visite à partir de la base."""
import sys
import threading

from flask import Flask, jsonify

import collecte
import exporter_page

app = Flask(__name__)

_collecte = {"en_cours": False, "journal": []}


@app.get("/")
def accueil():
    html, _ = exporter_page.page("local")
    return html


@app.post("/api/collecte")
def api_lancer_collecte():
    if _collecte["en_cours"]:
        return jsonify(ok=False, erreur="Une collecte est déjà en cours.")
    _collecte.update(en_cours=True, journal=[])

    def tourner():
        try:
            collecte.collecter(journal=lambda m: _collecte["journal"].append(m))
        except Exception as e:
            _collecte["journal"].append(f"Erreur : {e}")
        finally:
            _collecte["en_cours"] = False

    threading.Thread(target=tourner, daemon=True).start()
    return jsonify(ok=True)


@app.get("/api/collecte")
def api_etat_collecte():
    return jsonify(en_cours=_collecte["en_cours"], journal=_collecte["journal"][-1:])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("Ouvrez http://localhost:5000 dans votre navigateur.")
    app.run(port=5000, debug=False)
