import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import worker, { dispatchRefresh } from "../src/index.js";

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const env = { GITHUB_REFRESH_TOKEN: "test-only" };
function mock(runs, dispatchStatus = 204) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return url.includes("/runs?") ? Response.json({ workflow_runs: runs }) : new Response(null, { status: dispatchStatus });
  };
  return calls;
}
test("cron dispatches seven-day sync when stale", async () => {
  const calls = mock([]);
  await worker.scheduled({ cron: "*/5 * * * *" }, env);
  assert.equal(calls.length, 2);
  assert.equal(JSON.parse(calls[1].options.body).inputs.gmail_lookback_days, "7");
});
test("cron skips recently completed successful sync", async () => {
  const calls = mock([{ id: 1, status: "completed", conclusion: "success", updated_at: new Date().toISOString() }]);
  assert.equal((await dispatchRefresh(env, true)).status, "fresh");
  assert.equal(calls.length, 1);
});
test("manual refresh forces a 30-day scan even after recent success", async () => {
  const calls = mock([{ status: "completed", conclusion: "success", updated_at: new Date().toISOString() }]);
  const response = await worker.fetch(new Request("https://example.com/refresh", { method: "POST", headers: { Origin: "https://www.mandarineocean.cn" } }), env);
  assert.equal(response.status, 202);
  assert.equal(JSON.parse(calls[1].options.body).inputs.gmail_lookback_days, "30");
});
test("active job is reused instead of adding duplicate", async () => {
  const calls = mock([{ id: 123, status: "in_progress" }]);
  assert.deepEqual(await dispatchRefresh(env), { status: "running", run_id: "123" });
  assert.equal(calls.length, 1);
});
test("failed sync is retried, cron API failure is not swallowed", async () => {
  mock([{ status: "completed", conclusion: "failure", updated_at: new Date().toISOString() }], 403);
  await assert.rejects(worker.scheduled({ cron: "*/5 * * * *" }, env), /HTTP 403/);
});
test("unrelated browser origin cannot dispatch", async () => {
  const calls = mock([]);
  assert.equal((await worker.fetch(new Request("https://example.com/refresh", { method: "POST", headers: { Origin: "https://other.example" } }), env)).status, 403);
  assert.equal(calls.length, 0);
});
test("manual API error returns failure, not queued", async () => {
  mock([], 500);
  assert.equal((await worker.fetch(new Request("https://example.com/refresh", { method: "POST" }), env)).status, 502);
});
const context = vm.createContext({ Intl, Date });
vm.runInContext(readFileSync(new URL("../../docs/assets/data-refresh.js", import.meta.url), "utf8"), context);
const ui = context.MandarineRefresh;
test("UI distinguishes stale, failed and successful Gmail sync", () => {
  const status = { gmail_sync_ok: true, last_attempt_at_beijing: "2026-10-01T20:00:00+08:00" };
  assert.match(ui.healthText(status, Date.parse("2026-10-01T20:30:00+08:00")), /30 分钟未同步/);
  assert.match(ui.healthText(status, Date.parse("2026-10-01T20:01:00+08:00")), /同步成功/);
  assert.match(ui.healthText({ ...status, gmail_sync_ok: false }), /同步失败/);
});
test("old snapshot cannot claim a newly requested refresh completed", () => {
  const status = { run_id: "1", last_attempt_at_beijing: "2026-10-01T20:00:00+08:00" };
  const start = Date.parse("2026-10-01T21:00:00+08:00");
  assert.equal(Boolean(ui.completed(status, { status: "queued" }, start)), false);
  assert.equal(Boolean(ui.completed(status, { run_id: "1" }, start)), true);
});
