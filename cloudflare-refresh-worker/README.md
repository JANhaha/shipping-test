# Shipping refresh reliability

Cloudflare Cron checks every five minutes and dispatches the `stable` branch's
`update-shipping-data.yml`. It skips active jobs and successful runs completed
less than five minutes ago. GitHub's `17,47 * * * *` schedule remains a fallback.
These are check intervals, not guaranteed publication deadlines: runner queueing,
Gmail collection and Pages deployment add latency. Cron configuration can take
up to 15 minutes to propagate.

`GITHUB_REFRESH_TOKEN` is an existing Worker secret; it needs repository Actions
read/write permission. Never commit its value. Deploy with `wrangler deploy
--keep-vars` from this directory. Run `npm test` and `wrangler deploy --dry-run`
before deployment. `wrangler tail --format json` reports scheduled dispatches and
errors. Cron failures are not swallowed.

The three production data pages use `docs/assets/data-refresh.js`. Their buttons
request a real cloud sync, then poll the published `refresh_status.json` for a
matching run or a newer completion. They do not treat HTTP 202 as completed.
Gmail failure preserves cached data and publishes warning status, then fails
the workflow health-check step. The public status retains the last successful
sync time separately from the latest attempt. No new email can mean unchanged
source dates/prices even after a successful sync.

Local Flask templates use local API data and are not the production Pages UI.
