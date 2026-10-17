import { test } from "node:test";
import assert from "node:assert/strict";
import { matchRoute } from "../../static/js/lib/routes.js";
import { filtersFromSearch, searchFromFilters } from "../../static/js/lib/urlstate.js";
import { safeNext } from "../../static/js/lib/safe-next.js";
import * as f from "../../static/js/lib/format.js";
import { headline, gapNotice } from "../../static/js/lib/headline.js";

test("routes", () => {
  assert.deepEqual(matchRoute("/visits/V001912"), { name: "visit", params: { id: "V001912" }, access: "user" });
  assert.equal(matchRoute("/admin/users").access, "admin");
  assert.equal(matchRoute("/nope"), null);
  assert.equal(matchRoute("/visits/a/b"), null);
});

test("url state round-trips and drops defaults", () => {
  const s = "?from=2026-08-01&to=2026-08-31&type=interview&page=2";
  assert.deepEqual(filtersFromSearch(s), { from: "2026-08-01", to: "2026-08-31", type: "interview", page: 2 });
  assert.equal(searchFromFilters(filtersFromSearch(s)), s);
  assert.equal(searchFromFilters({ from: "", to: "", type: "", page: 1 }), "");
  assert.equal(filtersFromSearch("?page=abc").page, 1);
});

test("safeNext only allows same-site paths", () => {
  assert.equal(safeNext("/visits?type=guest"), "/visits?type=guest");
  for (const bad of ["//evil.example", "https://evil.example", "/\\evil.example", "javascript:alert(1)", "", null]) {
    assert.equal(safeNext(bad), "/visits", String(bad));
  }
});

test("formatting", () => {
  assert.equal(f.fmtDate("2026-08-12"), "Wed 12 Aug 2026");
  assert.equal(f.fmtLongDate("2026-08-12"), "Wednesday 12 August 2026");
  assert.equal(f.fmtTime("2026-08-12 09:05:00"), "09:05");
  assert.equal(f.fmtDuration(79), "1 h 19 min");
  assert.equal(f.fmtDuration(48), "48 min");
  assert.equal(f.fmtDuration(null), "Didn't sign out");
  assert.deepEqual([9, 12, 15].map(f.fmtHour), ["9 am", "12 pm", "3 pm"]);
  assert.equal(f.fmtCount(1953), "1,953");
  assert.equal(f.joinWords(["Tuesdays", "Wednesdays"]), "Tuesdays and Wednesdays");
  assert.deepEqual(f.dayRanges(["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-09-01"]),
    [["2026-08-10", "2026-08-13"], ["2026-09-01", "2026-09-01"]]);
});

const base = { total_visits: 1953, range: { from: "2026-07-01", to: "2026-09-30" },
  busiest_days: ["Tuesday", "Wednesday"], busiest_hours: [9], missing_days: [] };

test("headline", () => {
  assert.deepEqual(headline(base), {
    title: "The lobby is busiest on Tuesdays and Wednesdays, around 9 am.",
    subtitle: "1,953 visits from Wed 1 Jul 2026 to Wed 30 Sep 2026." });
  assert.equal(headline({ ...base, busiest_hours: [10, 11] }).title,
    "The lobby is busiest on Tuesdays and Wednesdays, around 10 am and 11 am.");
  assert.equal(headline({ ...base, total_visits: 0, busiest_days: [], busiest_hours: [] }).title, "No visits in this period.");
});

test("gap notice", () => {
  assert.equal(gapNotice([]), null);
  assert.equal(gapNotice(["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]),
    "The lobby iPad recorded no sign-ins from Mon 10 Aug 2026 to Thu 13 Aug 2026, so totals that include those days are incomplete.");
});

test("safeNext ignores control characters and backslashes that browsers rewrite into //", () => {
  for (const bad of ["/\t/evil.example", "/\n/evil.example", "/\r/evil.example", "/x\\evil"]) {
    assert.equal(safeNext(bad, "http://app.local"), "/visits", JSON.stringify(bad));
  }
  assert.equal(safeNext("/visits?type=guest#top", "http://app.local"), "/visits?type=guest#top");
});

test("a malformed percent-escape is not a route, not a crash", () => {
  assert.equal(matchRoute("/visits/%E0%A4%A"), null);
});
