// Bouton « Mettre à jour » (version Netlify) : une fonction Netlify lance la collecte sur GitHub ;
// à la fin, GitHub enregistre la nouvelle page et Netlify la remet en ligne.
const heure = iso => new Date(iso).toLocaleString("fr-FR", { weekday: "long", hour: "2-digit", minute: "2-digit" });
let suivi = null;

function afficherEtatMaj(e) {
  const p = $("#maj-etat"), b = $("#b-maj");
  if (!e || !e.status) { p.hidden = true; b.disabled = false; return; }
  if (e.status === "completed") {
    clearInterval(suivi); suivi = null;
    b.disabled = false;
    // Collecte terminée après la page affichée : Netlify met environ une minute à publier la nouvelle version.
    if (e.conclusion === "success" && (!D.maj || new Date(e.created_at) > new Date(D.maj))) {
      p.hidden = false;
      p.innerHTML = "<b>Mise à jour terminée.</b> La nouvelle page arrive dans une minute environ…";
      setTimeout(() => location.reload(), 60000);
    } else if (e.conclusion && e.conclusion !== "success") {
      p.hidden = false;
      p.innerHTML = `<b>La dernière mise à jour a échoué</b> (${heure(e.updated_at)}). Vous pouvez réessayer.`;
    } else {
      p.hidden = true;
    }
    return;
  }
  b.disabled = true; p.hidden = false;
  p.innerHTML = `<b>Mise à jour en cours</b> depuis ${heure(e.created_at)}. Comptez 15 à 25 minutes : la page se rechargera toute seule.`;
  if (!suivi) suivi = setInterval(lireEtat, 20000);
}

async function lireEtat() {
  try {
    const r = await fetch("/.netlify/functions/etat-maj");
    if (r.ok) afficherEtatMaj(await r.json());
  } catch {}
}

$("#b-maj").hidden = false;
$("#b-maj").onclick = async () => {
  $("#b-maj").disabled = true;
  const p = $("#maj-etat");
  try {
    const r = await fetch("/.netlify/functions/mettre-a-jour", { method: "POST" });
    const d = await r.json();
    if (!r.ok) throw new Error(d.erreur || "erreur");
    afficherEtatMaj({ status: "queued", created_at: new Date().toISOString() });
  } catch (err) {
    $("#b-maj").disabled = false; p.hidden = false;
    p.innerHTML = `La mise à jour n'a pas pu être lancée : ${esc(err.message)}.`;
  }
};
lireEtat();
