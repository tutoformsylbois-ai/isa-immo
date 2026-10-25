// État de la dernière collecte, lu par la page pour afficher « Mise à jour en cours ».
import { derniereCollecte, json } from "../lib/github.mjs";

export default async () => {
  try {
    return json(await derniereCollecte());
  } catch (e) {
    return json({ erreur: e.message }, 502);
  }
};
