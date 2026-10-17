// The filter form. Its values always come from the URL, and applying it writes the URL,
// so a filtered view is a link you can paste to a colleague.
import { h } from "../dom.js";
import { searchFromFilters } from "../lib/urlstate.js";

const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export function filterForm(filters, types, navigate) {
  const form = h("form", { class: "filters", "aria-label": "Filter visits" },
    h("label", {}, "From", h("input", { type: "date", name: "from", value: filters.from })),
    h("label", {}, "To", h("input", { type: "date", name: "to", value: filters.to })),
    h("label", {}, "Visit type",
      h("select", { name: "type" },
        h("option", { value: "" }, "All types"),
        types.map((t) => h("option", { value: t, selected: t === filters.type.toLowerCase() }, capital(t))))),
    h("div", { class: "form-actions" },
      h("button", { type: "submit", class: "button-primary" }, "Apply filters"),
      filters.from || filters.to || filters.type ? h("a", { href: "/visits" }, "Clear filters") : null),
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    navigate(`/visits${searchFromFilters({ from: data.get("from"), to: data.get("to"), type: data.get("type"), page: 1 })}`);
  });
  return form;
}

export { capital };
