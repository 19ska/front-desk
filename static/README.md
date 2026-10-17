# static/: the pages

A small single-page app with **no build step**: native ES modules, served by FastAPI.

## How it fits together

- `index.html` is the one shell. The server returns it for every page URL, so refresh and pasted links work.
- `js/router.js` handles History-API navigation. On each page it asks `/api/me` who you are:
  - signed out → `/login?next=…`
  - a viewer on an admin page → the no-access page

  **This guard is a courtesy. The API's 401/403 is the real control.**
- `js/api.js` is `fetch` with the session cookie. Any 401 sends you to sign in. Errors become readable messages.
- `js/pages/*.js` holds one module per page; each exports `render(container, ctx)`.
- `js/components/*.js` holds the nav, filter form, heatmap and visit table.
- `js/lib/*.js` is pure logic, unit-tested in `tests/js/`: route matching, URL ↔ filters, the safe post-login redirect, formatting, the headline sentence.

## Two rules

1. **All HTML is built with `h()` from `js/dom.js`, which only ever creates text nodes.** Data from the CSV (a
   visitor's name, say) can never be read as markup. There is no `innerHTML` anywhere.
2. **The page never decides what data you get.** The table shows whatever columns the API sent: a viewer's response
   has no visitor or host, so there's nothing to hide.

## Design

- `css/tokens.css` holds every colour, size and space, plus the mapping onto Web Awesome's variables. Restyle the app here.
- `css/app.css` holds layout and components, using tokens only.
- **UI library:** Web Awesome 3.14.0 from jsDelivr (pinned). Its `native.css` styles plain form controls and tables;
  only `wa-callout` and `wa-spinner` are components. If the CDN can't be reached, everything still works, just less styled.
- **Font:** Atkinson Hyperlegible Next, self-hosted in `fonts/` (SIL Open Font License, `fonts/OFL.txt`).
- **Heatmap colours:** one-hue ramp, checked with a palette validator (light end ≥ 2:1 against white).
- The design rationale is in [../docs/plan.md](../docs/plan.md) section 7b.
