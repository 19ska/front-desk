// After login, only ever go to a page on this site: never "//other.site" or "https://…".
// Control characters and backslashes are refused outright, because browsers strip or
// rewrite them (so "/\t/evil.example" would become "//evil.example").
export function safeNext(raw, origin = globalThis.location?.origin ?? "http://localhost") {
  if (typeof raw !== "string" || !raw.startsWith("/") || /[\u0000-\u001f\u007f\\]/.test(raw)) return "/visits";
  let url;
  try {
    url = new URL(raw, origin);
  } catch {
    return "/visits";
  }
  if (url.origin !== new URL(origin).origin) return "/visits";
  return url.pathname + url.search + url.hash;
}
