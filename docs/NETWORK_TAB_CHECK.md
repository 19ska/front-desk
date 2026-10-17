# Checking the network tab

The brief says hiding a column while the data is still in the response doesn't count, and that the reviewers will
look at the network tab. This page shows how to check that yourself in a browser: what a viewer's browser actually
**receives**, not just what the page shows.

**Short version:** sign in as the viewer, open DevTools → Network, and search *all responses* for a visitor's name.
There are 0 results. Do the same as the admin and the name is there. The page can't leak what it never receives.

---

## Before you start

1. Start the app: `.venv/bin/uvicorn app.main:app`
2. Create the test logins (in a second terminal): `.venv/bin/python scripts/create_test_accounts.py`
3. Have three identities ready that are definitely in the data. These three are on the first page of visits, as the
   admin sees it:
   - **Clara Haddad** (a visitor)
   - **Sofia Reyes** (a visitor)
   - **Oakfield Legal** (a visitor's company)

   Any name, email or company from `data/visits.csv` works; these are just easy ones.

## Chrome or Edge

1. Open a **private/incognito window** so no earlier session is used, and go to `http://127.0.0.1:8000`.
   You'll be sent to the sign-in page.
2. Open DevTools: **⌥⌘I** on Mac, **Ctrl+Shift+I** on Windows/Linux. Go to the **Network** tab.
3. In the Network tab:
   - tick **Preserve log**, so requests survive the page change after sign-in
   - click the **Fetch/XHR** filter, so you see API calls rather than images and fonts
4. Sign in as the **viewer**: `sam.ferreira@brightline.example` / `frontdesk-viewer`.
   You land on Visits. In the Network list you'll see `me`, `visit-types`, `stats?…` and `visits?…`.
5. Click the **`visits`** row, then the **Response** tab (or **Preview** for a tree view).
   Each item has `visit_id`, `date`, `signed_in`, `signed_out`, `duration_min`, `visit_type`, `host_team` and
   `pre_registered`. **There is no `visitor` and no `host`.**
6. Now search every response at once. Press **⌥⌘F** (Mac) or **Ctrl+Shift+F** (Windows/Linux) while the Network tab
   is focused, or click the **magnifying-glass** icon in the Network toolbar. A **Search** panel opens; it searches
   the bodies of every captured response, not just the URLs.
7. Search for `Clara Haddad`, then `Sofia Reyes`, then `Oakfield Legal`.
   **Expected: "No matches found" each time.**
8. Open a single visit: click the first date in the table (or go to `/visits/V001912`). A `V001912` request appears.
   Search again for `Sofia Reyes`. That's exactly who this visit is, and there are still no matches.
   The page shows "Guest" and "Hosted by the Finance team".
9. Try editing the URL to ask for a name: go to `/visits?visitor_name=Sofia`. The page shows the API's own refusal,
   *"Unknown filter: visitor_name. Use from, to, type, page, page_size."*, and the `visits?…` request in the
   Network tab has status **400**.
10. Try the admin page: go to `/admin/users`. The page says *"You don't have access to this page"*, and the nav has
    no link to it. Then check the API directly: in the **Console** tab, run
    ```js
    fetch("/api/admin/users").then(r => r.status)
    ```
    You get **403**. The page and the API both refuse. The API is the one doing the real work.

### The control: prove the search would have found them

11. Click **Sign out**, sign in as the **admin**: `dana.whitfield@brightline.example` / `frontdesk-admin`.
12. Repeat step 6 with the same three searches. **Now each one finds matches** inside the `visits?…` response.
    So the viewer's zero results mean the data isn't there, not that the search doesn't work.

### Optional: take a request to the terminal

Right-click any request → **Copy** → **Copy as cURL**, and paste it in a terminal. It replays with your session
cookie, so you can pipe it through `grep -ci "sofia reyes"`. As the viewer you get `0`.

## Firefox

Same steps:
- **⌥⌘E** / **Ctrl+Shift+E** opens the Network tab
- filter **XHR**
- tick **Persist Logs** (in the gear menu)
- the **Response** tab shows the body
- to search all bodies, use the **Search** (magnifying-glass) icon in the Network toolbar

## Safari

Turn on *Settings → Advanced → Show features for web developers*. Then **⌥⌘I** → **Network**, filter **XHR/Fetch**,
and tick **Preserve Log**. Select a request and look at **Response**. Safari's Network search box filters by URL, so
use **⌘F inside the Response view** to search a body.

---

## Why this passes, and why hiding a column wouldn't

A common shortcut is to send every field and have the page skip the name column. The table looks right, but the
names are still in the response, and this exact check finds them.

Here, the server decides before reading from the database. For a viewer, the query only selects the allowed
columns (`app/visits.py`, `VIEWER_COLUMNS`), so the response is built without identities in the first place. The page
then simply draws whichever columns it was sent. The same is true for a single visit (`/api/visits/:id`) and for
stats, which only ever contain counts.

For the same check with curl, including a search for **every** name in the data rather than three, see
[TESTING_WITH_CURL.md](TESTING_WITH_CURL.md) section 6.
