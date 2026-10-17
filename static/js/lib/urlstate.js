// The visits page keeps its whole state in the URL, so a pasted link opens exactly the same view.
const KEYS = ["from", "to", "type"];

export function filtersFromSearch(search) {
  const params = new URLSearchParams(search);
  const page = Number.parseInt(params.get("page") || "1", 10);
  return {
    from: params.get("from") || "",
    to: params.get("to") || "",
    type: params.get("type") || "",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  };
}

export function searchFromFilters(filters) {
  const params = new URLSearchParams();
  for (const key of KEYS) if (filters[key]) params.set(key, filters[key]);
  if (filters.page && filters.page > 1) params.set("page", String(filters.page));
  const s = params.toString();
  return s ? `?${s}` : "";
}
