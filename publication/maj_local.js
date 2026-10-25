// Bouton « Mettre à jour » (application locale, app.py) : lance la collecte sur l'ordinateur et recharge la page à la fin.
$("#b-maj").hidden = false;
$("#b-maj").onclick = async () => {
  const p = $("#maj-etat"), b = $("#b-maj");
  const r = await fetch("/api/collecte", { method: "POST" }).then(r => r.json());
  if (!r.ok) { p.hidden = false; p.textContent = r.erreur; return; }
  b.disabled = true; p.hidden = false;
  const suivi = setInterval(async () => {
    const s = await fetch("/api/collecte").then(r => r.json());
    p.innerHTML = `<b>Mise à jour en cours</b> (10 à 20 minutes) : ${esc(s.journal.at(-1) || "démarrage…")}`;
    if (!s.en_cours) { clearInterval(suivi); location.reload(); }
  }, 3000);
};
