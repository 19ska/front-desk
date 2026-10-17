// Every page the app has, who may open it, and how its URL is read.
// "access" is a courtesy for the user; the API is what actually refuses.
const ROUTES = [
  { name: "login", pattern: /^\/login$/, access: "public" },
  { name: "signup", pattern: /^\/signup$/, access: "public" },
  { name: "visits", pattern: /^\/visits$/, access: "user" },
  { name: "visit", pattern: /^\/visits\/([^/]+)$/, access: "user", keys: ["id"] },
  { name: "users", pattern: /^\/admin\/users$/, access: "admin" },
];

export function matchRoute(path) {
  for (const route of ROUTES) {
    const m = route.pattern.exec(path);
    if (!m) continue;
    const params = {};
    try {
      (route.keys || []).forEach((key, i) => { params[key] = decodeURIComponent(m[i + 1]); });
    } catch {
      return null; // a malformed %-escape: treat as "page not found", never a frozen page
    }
    return { name: route.name, params, access: route.access };
  }
  return null;
}
