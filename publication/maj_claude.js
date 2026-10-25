// Bouton « Mettre à jour » (version claude.ai) : la page enregistre une demande ; une tâche planifiée
// sur l'ordinateur la voit, relance la collecte et republie la page (qui se recharge alors toute seule).
const heure = iso => new Date(iso).toLocaleString("fr-FR", { weekday: "long", hour: "2-digit", minute: "2-digit" });
function afficherEtatMaj(e) {
  const p = $("#maj-etat"), b = $("#b-maj");
  if (!e || e.statut === "termine" || !e.statut) { p.hidden = true; b.disabled = false; return; }
  b.disabled = true; p.hidden = false;
  p.innerHTML = e.statut === "en_cours"
    ? `<b>Mise à jour en cours</b> depuis ${heure(e.debut)}. Comptez une dizaine de minutes : la page se rechargera toute seule.`
    : `<b>Mise à jour demandée</b> ${heure(e.demandee)}. Elle démarre dans l'heure, si l'ordinateur et l'application Claude sont allumés.`;
}
(async () => {
  const db = await claude.use("db");
  if (!db) return;
  const ref = db.doc("maj/etat");
  $("#b-maj").hidden = false;
  ref.onSnapshot(s => afficherEtatMaj(s.exists ? s.data() : null), () => { $("#b-maj").hidden = true; });
  $("#b-maj").onclick = async () => {
    $("#b-maj").disabled = true;
    try {
      await ref.set({ statut: "en_attente", demandee: new Date().toISOString() });
    } catch (err) {
      $("#b-maj").disabled = false;
      const p = $("#maj-etat"); p.hidden = false;
      p.innerHTML = err?.code === "invalid_argument"
        ? "Votre accès à cette page ne permet pas de demander une mise à jour."
        : "La demande n'a pas pu être enregistrée. Réessayez dans un instant.";
    }
  };
})();
