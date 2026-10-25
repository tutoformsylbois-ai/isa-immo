// Bouton « Mettre à jour » : lance la collecte sur GitHub, sauf si une collecte tourne déjà,
// vient de se terminer, ou si le bouton a déjà servi 3 fois aujourd'hui (la page peut être publique).
import { derniereCollecte, github, json } from "../lib/github.mjs";

const DELAI_MIN = 15;
const MAX_PAR_JOUR = 3;

// Minuit à Paris, en heure UTC (format attendu par le filtre « created » de GitHub).
function minuitParis() {
  const maintenant = new Date();
  const vu = fuseau => new Date(maintenant.toLocaleString("en-US", { timeZone: fuseau }));
  const paris = vu("Europe/Paris");
  const decalage = paris - vu("UTC");
  const minuit = Date.UTC(paris.getFullYear(), paris.getMonth(), paris.getDate()) - decalage;
  return new Date(minuit).toISOString().replace(".000Z", "Z");
}

export default async (req) => {
  if (req.method !== "POST") return json({ erreur: "Méthode non autorisée" }, 405);
  try {
    const d = await derniereCollecte();
    if (d.status && d.status !== "completed") return json({ ok: true, deja: "en cours" });
    if (d.created_at && Date.now() - new Date(d.created_at) < DELAI_MIN * 60000) {
      return json({ erreur: `une mise à jour a déjà été faite il y a moins de ${DELAI_MIN} minutes` }, 429);
    }
    // Seuls les lancements par le bouton comptent ; la collecte automatique du matin est à part.
    const aujourdhui = await github(`/runs?event=workflow_dispatch&created=>=${minuitParis()}&per_page=10`);
    if (aujourdhui.total_count >= MAX_PAR_JOUR) {
      return json({ erreur: `le bouton a déjà servi ${MAX_PAR_JOUR} fois aujourd'hui ; la collecte automatique a lieu demain matin` }, 429);
    }
    await github("/dispatches", { method: "POST", body: JSON.stringify({ ref: "main" }) });
    return json({ ok: true, restantes: MAX_PAR_JOUR - aujourdhui.total_count - 1 });
  } catch (e) {
    return json({ erreur: e.message }, 502);
  }
};
