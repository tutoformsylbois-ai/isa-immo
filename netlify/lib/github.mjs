// Accès à GitHub pour les fonctions Netlify. Le jeton reste côté serveur (variable GITHUB_TOKEN).
const WORKFLOW = "collecte.yml";

export async function github(chemin, options = {}) {
  const depot = process.env.GITHUB_REPO;
  const r = await fetch(`https://api.github.com/repos/${depot}/actions/workflows/${WORKFLOW}${chemin}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "isa-immo",
      ...(options.headers || {}),
    },
  });
  if (!r.ok && r.status !== 204) throw new Error(`GitHub a répondu ${r.status}`);
  return r.status === 204 ? null : r.json();
}

export async function derniereCollecte() {
  const d = await github("/runs?per_page=1");
  const run = d.workflow_runs[0];
  if (!run) return {};
  return { status: run.status, conclusion: run.conclusion, created_at: run.created_at, updated_at: run.updated_at };
}

export const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
