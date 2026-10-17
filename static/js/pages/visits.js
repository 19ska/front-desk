// Where everyone lands: when the lobby is busy, then the visits themselves.
// All state comes from the URL; the server does every filter and count.
import { api } from "../api.js";
import { filterForm } from "../components/filters.js";
import { heatmap } from "../components/heatmap.js";
import { visitTable } from "../components/table.js";
import { clear, h } from "../dom.js";
import { fmtCount, fmtDuration } from "../lib/format.js";
import { gapNotice, headline } from "../lib/headline.js";
import { filtersFromSearch, searchFromFilters } from "../lib/urlstate.js";

export const LAST_LIST_KEY = "fd:lastList";

function loading(text) {
  return h("div", { class: "loading" }, h("wa-spinner", {}), h("span", {}, text));
}

function remember(url) {
  try {
    sessionStorage.setItem(LAST_LIST_KEY, url);
  } catch {
    /* storage can be unavailable; "Back to visits" then falls back to /visits */
  }
}

function pager(list, filters) {
  const first = (list.page - 1) * list.page_size + 1;
  const last = Math.min(list.page * list.page_size, list.total);
  const link = (page, label) => (page >= 1 && page <= list.total_pages
    ? h("a", { href: `/visits${searchFromFilters({ ...filters, page })}`, rel: label === "Next" ? "next" : "prev" }, label)
    : h("span", { class: "muted", "aria-disabled": "true" }, label));
  return h("nav", { class: "pager", "aria-label": "Pages" },
    h("span", {}, `Showing ${fmtCount(first)}–${fmtCount(last)} of ${fmtCount(list.total)}`),
    h("span", { class: "pager-links" }, link(list.page - 1, "Previous"), link(list.page + 1, "Next")),
  );
}

export async function render(container, { navigate }) {
  const filters = filtersFromSearch(location.search);
  remember(location.pathname + location.search);
  container.append(loading("Loading visits…"));

  let types = [];
  let stats;
  let list;
  try {
    types = (await api("/api/visit-types")).visit_types;
    [stats, list] = await Promise.all([
      api(`/api/stats${searchFromFilters({ ...filters, page: 1 })}`),
      api(`/api/visits${searchFromFilters(filters)}`),
    ]);
  } catch (e) {
    if (e.status === 401) return "Visits";
    clear(container);
    container.append(
      h("h1", { class: "page-title" }, "Visits"),
      h("div", { class: "stack" },
        h("wa-callout", { variant: "danger" }, e.message),
        filterForm(filters, types, navigate)),
    );
    return "Visits";
  }

  const { title, subtitle } = headline(stats);
  const notice = gapNotice(stats.missing_days);
  const length = stats.visit_length;
  clear(container);
  // Optional sections are null when there's nothing to show; native append() would print "null".
  container.append(...[
    h("header", { class: "intro" },
      h("h1", { class: "headline" }, title),
      h("p", { class: "lede" }, subtitle)),
    stats.total_visits ? heatmap(stats) : null,
    h("div", { class: "facts" },
      length.measured_visits
        ? h("p", {}, `Median visit: ${fmtDuration(length.median_min)}, based on the ${fmtCount(length.measured_visits)} `
          + `visit${length.measured_visits === 1 ? "" : "s"} where the guest signed out.`)
        : null,
      notice ? h("wa-callout", { variant: "warning" }, notice) : null),
    h("section", { class: "list", "aria-labelledby": "list-title" },
      h("h2", { id: "list-title", class: "section-title" }, "Visits"),
      filterForm(filters, types, navigate),
      list.total
        ? [visitTable(list.items), pager(list, filters)]
        : h("p", { class: "empty" }, "No visits match these filters. Try a wider date range.")),
  ].filter(Boolean));
  return "Visits";
}
