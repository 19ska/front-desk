// One visit, laid out like the badge a guest wears. An admin sees the person;
// a viewer's API response has no person in it, so the badge is titled by the visit's type.
import { api } from "../api.js";
import { capital } from "../components/filters.js";
import { h } from "../dom.js";
import { fmtDuration, fmtLongDate, fmtTime } from "../lib/format.js";
import { LAST_LIST_KEY } from "./visits.js";

function backHref() {
  try {
    return sessionStorage.getItem(LAST_LIST_KEY) || "/visits";
  } catch {
    return "/visits";
  }
}

function times(v) {
  return v.signed_out
    ? `${fmtTime(v.signed_in)} to ${fmtTime(v.signed_out)} (${fmtDuration(v.duration_min)})`
    : `Signed in at ${fmtTime(v.signed_in)}, didn't sign out`;
}

export async function render(container, { params }) {
  const back = h("p", {}, h("a", { href: backHref() }, "Back to visits"));
  container.append(h("div", { class: "loading" }, h("wa-spinner", {}), h("span", {}, "Loading visit…")));
  let v;
  try {
    v = await api(`/api/visits/${encodeURIComponent(params.id)}`);
  } catch (e) {
    if (e.status === 401) return "Visit";
    container.replaceChildren(
      h("h1", { class: "page-title" }, e.status === 404 ? "Visit not found" : "Couldn't load this visit"),
      h("p", {}, e.status === 404 ? `${e.message} Check the link, or go back to the list.` : e.message),
      back,
    );
    return "Visit not found";
  }

  const person = v.visitor
    ? [h("p", { class: "badge-sub" }, v.visitor.email), h("p", { class: "badge-sub" }, v.visitor.company)]
    : [];
  const host = v.host ? `Hosted by ${v.host.name} (${v.host_team})` : `Hosted by the ${v.host_team} team`;
  container.replaceChildren(
    h("article", { class: "badge" },
      h("p", { class: "badge-kind" }, v.visitor ? capital(v.visit_type) : "Visit"),
      h("h1", { class: "badge-title" }, v.visitor ? v.visitor.name : capital(v.visit_type)),
      person,
      h("dl", { class: "badge-facts" },
        h("dt", {}, "Date"), h("dd", {}, fmtLongDate(v.date)),
        h("dt", {}, "Time"), h("dd", {}, times(v)),
        h("dt", {}, "Host"), h("dd", {}, host),
        h("dt", {}, "Pre-registered"), h("dd", {}, v.pre_registered ? "Yes" : "No")),
    ),
    back,
  );
  return v.visitor ? v.visitor.name : `${capital(v.visit_type)} visit`;
}
