// The visit list. Which columns exist depends on what the API sent: a viewer's
// response has no visitor or host at all, so there is nothing here to hide.
import { h } from "../dom.js";
import { fmtDate, fmtDuration, fmtTime } from "../lib/format.js";
import { capital } from "./filters.js";

const VIEWER = [
  ["Date", (v) => h("a", { href: `/visits/${encodeURIComponent(v.visit_id)}` }, fmtDate(v.date))],
  ["Signed in", (v) => fmtTime(v.signed_in)],
  ["Signed out", (v) => (v.signed_out ? fmtTime(v.signed_out) : h("span", { class: "muted" }, "Didn't sign out"))],
  ["Length", (v) => (v.duration_min === null ? "—" : fmtDuration(v.duration_min))],
  ["Type", (v) => capital(v.visit_type)],
  ["Team", (v) => v.host_team],
  ["Pre-registered", (v) => (v.pre_registered ? "Yes" : "No")],
];

const ADMIN = [
  VIEWER[0],
  ["Visitor", (v) => v.visitor.name],
  ["Company", (v) => v.visitor.company],
  ["Host", (v) => v.host.name],
  ...VIEWER.slice(1, 6),
];

export function visitTable(items) {
  const columns = items.length && items[0].visitor ? ADMIN : VIEWER;
  return h("div", { class: "scroll-x" },
    h("table", { class: "visits" },
      h("thead", {}, h("tr", {}, columns.map(([label]) => h("th", { scope: "col" }, label)))),
      h("tbody", {}, items.map((v) => h("tr", {}, columns.map(([, cell]) => h("td", {}, cell(v)))))),
    ),
  );
}
