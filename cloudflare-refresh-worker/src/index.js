const ORIGIN = "https://www.mandarineocean.cn";
const WORKFLOW = "https://api.github.com/repos/JANhaha/shipping-test/actions/workflows/update-shipping-data.yml";
const headers = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Cache-Control": "no-store",
};

async function github(env, path, options = {}) {
  if (!env.GITHUB_REFRESH_TOKEN) throw new Error("Refresh credential is not configured");
  const response = await fetch(`${WORKFLOW}${path}`, {
    ...options,
    signal: AbortSignal.timeout(20000),
    headers: {
      Authorization: `Bearer ${env.GITHUB_REFRESH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "mandarine-refresh",
    },
  });
  if (!response.ok) throw new Error(`GitHub request failed: HTTP ${response.status}`);
  return response;
}

export async function dispatchRefresh(env, scheduled = false) {
  const response = await github(env, "/runs?branch=stable&per_page=10");
  const { workflow_runs: runs } = await response.json();
  if (!Array.isArray(runs)) throw new Error("Invalid GitHub workflow response");
  const active = runs.find(run => run.status !== "completed");
  if (active) return { status: "running", run_id: String(active.id) };
  const recent = runs.find(run => run.conclusion === "success");
  if (scheduled && recent && Date.now() - Date.parse(recent.updated_at) < 5 * 60000) {
    return { status: "fresh", run_id: String(recent.id) };
  }
  await github(env, "/dispatches", {
    method: "POST",
    body: JSON.stringify({ ref: "stable", inputs: { gmail_lookback_days: scheduled ? "7" : "30" } }),
  });
  return { status: "queued" };
}

export default {
  async scheduled(controller, env) {
    // Await failures so Cloudflare records failed invocations, not false successes.
    const result = await dispatchRefresh(env, true);
    console.log(JSON.stringify({ event: "scheduled-refresh", cron: controller.cron, ...result }));
  },
  async fetch(request, env) {
    if (new URL(request.url).pathname !== "/refresh") return new Response("Not found", { status: 404, headers });
    if (request.method === "OPTIONS") return new Response(null, { headers });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers });
    const origin = request.headers.get("Origin");
    if (origin && origin !== ORIGIN) return new Response("Forbidden", { status: 403, headers });
    try {
      return Response.json(await dispatchRefresh(env), { status: 202, headers });
    } catch (error) {
      console.error("refresh-dispatch-failed", error.message);
      return Response.json({ status: "error", message: "云端刷新提交失败，请稍后重试。" }, { status: 502, headers });
    }
  },
};
