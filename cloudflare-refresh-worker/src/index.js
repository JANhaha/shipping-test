const ORIGIN = "https://www.mandarineocean.cn";
const headers = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Cache-Control": "no-store",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }
    if (request.method !== "POST" || new URL(request.url).pathname !== "/refresh") {
      return new Response("Not found", { status: 404, headers });
    }

    const response = await fetch(
      "https://api.github.com/repos/JANhaha/shipping-test/actions/workflows/update-shipping-data.yml/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_REFRESH_TOKEN}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "mandarine-refresh",
        },
        body: JSON.stringify({
          ref: "stable",
          inputs: { gmail_lookback_days: "30" },
        }),
      },
    );

    return Response.json(
      response.ok ? { status: "queued" } : { status: "error" },
      { status: response.ok ? 202 : 502, headers },
    );
  },
};
