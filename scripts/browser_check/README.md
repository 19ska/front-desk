# scripts/browser_check/

Checks the real pages in **headless Google Chrome**, with no npm packages. `cdp.mjs` talks to Chrome over the
DevTools protocol using Node's built-in `WebSocket`.

```bash
scripts/browser_check/serve-fresh.sh                        # app on :8765 with a throwaway database (var/check.db)
node scripts/browser_check/run.mjs                          # all scenarios → "52 passed, 0 failed"
node scripts/browser_check/run.mjs http://127.0.0.1:8765 visits detail   # only some scenarios
pkill -f frontdesk-check-server                             # stop the server
```

Needs Node 22+ and Chrome at `/Applications/Google Chrome.app` (or set `CHROME=/path/to/chrome`).
**Start from a fresh server each time**, since the `auth` scenario signs people up.

| Scenario | Checks |
|---|---|
| `auth` | login redirect with `next`, refusal message, sign-up, viewer nav and no-access page, API 403 from the browser, 404 page |
| `visits` | headline, heatmap, viewer columns and network response without identities, filters in the URL, back/forward, pasted links, page 3 refresh, bad-range message, empty state, 400px width, admin columns |
| `detail` | single-visit refresh, Back keeps filters, viewer badge without identity, friendly not-found, admin badge, people with access |
| `hygiene` | no raw field names, `null` or `undefined` on any page for either role; visible focus ring |
| `resilience` | hostile `next=`, malformed URLs, a simulated server error (request interception) never leaves a blank page |

Screenshots of every page land in `var/screenshots/`.

Expected 401, 403 and 404 responses are logged by Chrome as network errors. The checker ignores those (they're the
access rules working) but fails on any JavaScript exception or `console.error`.
