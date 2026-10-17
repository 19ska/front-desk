// Drives the real app in headless Chrome and checks the brief's page rules.
// Start a server with a fresh database first (see README), then:
//   node scripts/browser_check/run.mjs [base-url]
// Screenshots land in var/screenshots/.
import { launch } from "./cdp.mjs";

const BASE = process.argv[2] || "http://127.0.0.1:8765";
const SHOTS = "var/screenshots";
const SAM = { email: "sam.ferreira@brightline.example", password: "frontdesk-viewer" };
const DANA = { email: "dana.whitfield@brightline.example", password: "frontdesk-admin" };

const results = [];
function check(name, ok, detail = "") {
  results.push({ name, ok });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok || !detail ? "" : `  (${detail})`}`);
}

const where = (page) => page.eval("location.pathname + location.search");
const text = (page, sel) => page.eval(`document.querySelector(${JSON.stringify(sel)})?.textContent.trim() ?? null`);

async function submit(page, values) {
  await page.eval(`(() => {
    const form = document.querySelector("main form");
    for (const [k, v] of Object.entries(${JSON.stringify(values)})) form.elements[k].value = v;
    form.requestSubmit();
  })()`);
}

async function signIn(page, who, next = "/visits") {
  await page.goto(`${BASE}/login?next=${encodeURIComponent(next)}`);
  await page.settled();
  await submit(page, who);
  await page.waitFor(`location.pathname !== "/login"`);
  await page.settled();
}

async function signOut(page) {
  await page.eval(`[...document.querySelectorAll("#nav button")].find(b => b.textContent === "Sign out").click()`);
  await page.waitFor(`location.pathname === "/login"`);
  await page.settled();
}

async function authChecks(page) {
  await page.goto(`${BASE}/visits`);
  await page.settled();
  check("signed out /visits goes to login with next", (await where(page)) === "/login?next=%2Fvisits", await where(page));
  await page.screenshot(`${SHOTS}/login.png`);

  await page.goto(`${BASE}/signup?next=%2Fvisits`);
  await page.settled();
  await submit(page, { email: "stranger@example.com", password: "whatever123" });
  await page.waitFor(`document.querySelector("main wa-callout") && customElements.get("wa-callout")`);
  await page.settled();
  check("stranger sign-up shows the agreed refusal",
    (await text(page, "main wa-callout")) === "This email isn't on Brightline's access list. If you think it should be, ask Dana.");
  await page.screenshot(`${SHOTS}/signup-refused.png`);

  for (const who of [SAM, DANA]) {
    await page.goto(`${BASE}/signup?next=%2Fvisits`);
    await page.settled();
    await submit(page, who);
    await page.waitFor(`location.pathname === "/visits"`);
    await page.settled();
    await signOut(page);
  }
  check("Sam and Dana can sign up", true);

  await signIn(page, SAM);
  check("viewer lands on /visits", (await where(page)) === "/visits");
  const navText = await text(page, "#nav");
  check("viewer nav has no 'People with access'", !navText.includes("People with access"), navText);
  await page.goto(`${BASE}/admin/users`);
  await page.settled();
  check("viewer on /admin/users sees no-access page", (await text(page, "main h1")) === "You don't have access to this page");
  await page.screenshot(`${SHOTS}/noaccess-viewer.png`);
  const status = await page.eval(`fetch("/api/admin/users").then(r => r.status)`);
  check("viewer calling /api/admin/users from the browser gets 403", status === 403, String(status));

  await page.goto(`${BASE}/whatever/here`);
  await page.settled();
  check("unknown URL shows Page not found", (await text(page, "main h1")) === "Page not found");
  await page.screenshot(`${SHOTS}/notfound.png`);

  await signOut(page);
  await signIn(page, SAM, "/visits?type=guest");
  check("login returns to the page you wanted", (await where(page)) === "/visits?type=guest", await where(page));
  await signOut(page);

  await signIn(page, DANA);
  check("admin nav shows 'People with access'", (await text(page, "#nav")).includes("People with access"));
  await signOut(page);
}

async function visitsChecks(page) {
  await signIn(page, SAM);
  check("headline answers the question",
    (await text(page, "main h1")) === "The lobby is busiest on Tuesdays and Wednesdays, around 9 am.", await text(page, "main h1"));
  const hottest = await page.eval(`[...document.querySelectorAll("td.heat-5")].map(td => td.dataset.label)`);
  check("darkest heatmap cell includes Tuesday 9 am", hottest.some((l) => l.startsWith("Tuesday 9 am")), hottest.join("; "));
  const headers = await page.eval(`[...document.querySelectorAll("table.visits th")].map(th => th.textContent)`);
  check("viewer table has no Visitor, Company or Host column", !headers.some((x) => ["Visitor", "Company", "Host"].includes(x)), headers.join(","));
  const raw = await page.eval(`fetch("/api/visits?page_size=200").then(r => r.text())`);
  check("viewer's network response has no visitor or host key", !raw.includes('"visitor"') && !raw.includes('"host"'));
  await page.screenshot(`${SHOTS}/visits-viewer.png`);

  await submit(page, { from: "2026-08-01", to: "2026-08-31", type: "interview" });
  await page.waitFor(`location.search.includes("type=interview")`);
  await page.settled();
  const filtered = "/visits?from=2026-08-01&to=2026-08-31&type=interview";
  check("applying filters writes them to the URL", (await where(page)) === filtered, await where(page));
  check("filtered list shows 115 visits", (await text(page, ".pager")).includes("of 115"), await text(page, ".pager"));
  check("gap notice shows for August", (await text(page, "wa-callout[variant=warning]"))?.startsWith("The lobby iPad recorded no sign-ins"));
  await page.screenshot(`${SHOTS}/visits-filtered.png`);

  await page.eval("history.back()");
  await page.waitFor(`location.search === ""`);
  await page.settled();
  check("Back returns to the unfiltered list", (await where(page)) === "/visits");
  await page.eval("history.forward()");
  await page.waitFor(`location.search.includes("type=interview")`);
  await page.settled();
  check("Forward returns to the filtered list", (await where(page)) === filtered);

  await page.goto(`${BASE}${filtered}`);
  await page.settled();
  const values = await page.eval(`(() => { const f = document.querySelector("form.filters").elements; return [f.from.value, f.to.value, f.type.value].join("|"); })()`);
  check("pasted filtered link opens filtered", values === "2026-08-01|2026-08-31|interview" && (await text(page, ".pager")).includes("of 115"), values);

  await page.goto(`${BASE}/visits?page=3`);
  await page.settled();
  check("refresh on page 3 stays on page 3", (await text(page, ".pager")).startsWith("Showing 101–150"), await text(page, ".pager"));

  await page.goto(`${BASE}/visits?from=2026-08-31&to=2026-08-01`);
  await page.settled();
  check("bad pasted range shows the API's message",
    (await text(page, "wa-callout[variant=danger]")) === "The end date (2026-08-01) is before the start date (2026-08-31).");

  await page.goto(`${BASE}/visits?from=2026-08-10&to=2026-08-13`);
  await page.settled();
  check("gap-only range shows an honest empty state",
    (await text(page, "main h1")) === "No visits in this period." && (await text(page, ".empty"))?.startsWith("No visits match"));
  await page.screenshot(`${SHOTS}/visits-empty.png`);

  await page.setViewport(400);
  await page.goto(`${BASE}/visits`);
  await page.settled();
  const overflow = await page.eval("document.documentElement.scrollWidth");
  check("no page-wide horizontal scroll at 400px", overflow <= 400, String(overflow));
  await page.screenshot(`${SHOTS}/visits-mobile.png`);
  await page.setViewport(1280);
  await signOut(page);

  await signIn(page, DANA);
  const adminHeaders = await page.eval(`[...document.querySelectorAll("table.visits th")].map(th => th.textContent)`);
  check("admin table shows Visitor, Company and Host", ["Visitor", "Company", "Host"].every((x) => adminHeaders.includes(x)), adminHeaders.join(","));
  await page.screenshot(`${SHOTS}/visits-admin.png`);
  await signOut(page);
}

async function detailChecks(page) {
  await signIn(page, SAM, "/visits?type=guest");
  await page.eval(`document.querySelector("table.visits tbody a").click()`);
  await page.waitFor(`location.pathname.startsWith("/visits/V")`);
  await page.settled();
  const opened = await where(page);
  await page.goto(`${BASE}${opened}`);
  await page.settled();
  check("refresh on a single visit stays there", (await where(page)) === opened, await where(page));
  await page.eval(`[...document.querySelectorAll("main a")].find(a => a.textContent === "Back to visits").click()`);
  await page.waitFor(`location.pathname === "/visits"`);
  await page.settled();
  check("Back to visits keeps the filters", (await where(page)) === "/visits?type=guest", await where(page));

  await page.goto(`${BASE}/visits/V001912`);
  await page.settled();
  const badge = await text(page, "main .badge");
  check("viewer badge has no name, email, company or host name",
    !/Sofia|Reyes|oakfield|Nadia/i.test(badge) && badge.includes("Hosted by the Finance team"), badge);
  const raw = await page.eval(`fetch("/api/visits/V001912").then(r => r.text())`);
  check("viewer's visit response has no visitor key", !raw.includes('"visitor"'));
  await page.screenshot(`${SHOTS}/visit-viewer.png`);

  await page.goto(`${BASE}/visits/V001996`);
  await page.settled();
  check("deduplicated id shows a friendly not-found", (await text(page, "main h1")) === "Visit not found");
  await signOut(page);

  await signIn(page, DANA, "/visits/V001912");
  check("admin badge shows the visitor", (await text(page, "main h1")) === "Sofia Reyes"
    && (await text(page, "main .badge")).includes("Hosted by Nadia Ferreira (Finance)"));
  await page.screenshot(`${SHOTS}/visit-admin.png`);
  await page.goto(`${BASE}/admin/users`);
  await page.settled();
  const rows = await page.eval(`[...document.querySelectorAll("main tbody tr")].map(r => r.textContent)`);
  check("admin sees 8 people, Sam and Dana signed up",
    rows.length === 8 && rows.filter((r) => r.endsWith("Yes")).length === 2, rows.join(" | "));
  await page.screenshot(`${SHOTS}/users-admin.png`);
  await signOut(page);
}

async function hygieneChecks(page) {
  const pages = ["/visits", "/visits?type=vendor&from=2026-08-01&to=2026-08-31", "/visits/V001912", "/visits/V001909",
    "/visits?from=2026-08-10&to=2026-08-13", "/admin/users", "/nope"];
  const leftovers = /signed_out_at|signed_in_at|visit_type|host_team|pre_registered|duration_min|\bnull\b|\bundefined\b|\bNaN\b|\[object/;
  for (const who of [SAM, DANA]) {
    await signIn(page, who);
    for (const url of pages) {
      await page.goto(`${BASE}${url}`);
      await page.settled();
      const body = await page.eval("document.body.innerText");
      const hit = body.match(leftovers);
      check(`no field names or null/undefined on ${url} (${who === SAM ? "viewer" : "admin"})`, !hit, hit && hit[0]);
    }
    await signOut(page);
  }
  await page.goto(`${BASE}/login`);
  await page.settled();
  await page.eval(`document.querySelector("main input").focus()`);
  const ring = await page.eval(`(() => { const s = getComputedStyle(document.activeElement); return s.outlineStyle + " " + s.outlineWidth; })()`);
  check("keyboard focus shows a visible ring", !ring.startsWith("none") && parseFloat(ring.split(" ")[1]) >= 2, ring);
}

async function resilienceChecks(page) {
  await page.goto(`${BASE}/login?next=${encodeURIComponent("/\t/evil.example")}`);
  await page.settled();
  await submit(page, SAM);
  await page.waitFor(`location.pathname !== "/login"`).catch(() => {});
  await page.settled().catch(() => {});
  check("a next= with a hidden tab is ignored and sign-in still works", (await where(page)) === "/visits", await where(page));

  await page.goto(`${BASE}/visits/%E0%A4%A`);
  await page.settled().catch(() => {});
  check("a broken %-escape in the URL shows Page not found", (await text(page, "main h1")) === "Page not found", await text(page, "main h1"));

  await page.goto(`${BASE}/visits/V001996`);
  await page.settled();
  check("visit-not-found copy assumes nothing about this dataset", !(await text(page, "main")).includes("duplicate"), await text(page, "main p"));

  await page.failRequests("/api/me", 500);
  await page.goto(`${BASE}/login`);
  await page.settled().catch(() => {});
  check("a server error on load shows a message, not a blank page",
    (await text(page, "main h1")) === "Something went wrong" && (await text(page, "main")).includes("Something went wrong on our side"), await text(page, "main"));
  await page.stopFailing();
  page.errors.length = 0; // the simulated 500 is expected to log
  await page.goto(`${BASE}/visits`);
  await page.settled();
  await signOut(page);
}

const SCENARIOS = { auth: authChecks, visits: visitsChecks, detail: detailChecks, hygiene: hygieneChecks, resilience: resilienceChecks };

const { page, close } = await launch();
try {
  await page.setViewport(1280);
  const wanted = process.argv.slice(3);
  for (const [name, run] of Object.entries(SCENARIOS)) {
    if (wanted.length && !wanted.includes(name)) continue;
    await run(page);
  }
  check("no errors in the browser console", page.errors.length === 0, page.errors.join(" | "));
} catch (e) {
  check("scenario ran to the end", false, e.message);
} finally {
  await close();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
