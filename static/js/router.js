// History-API router. Every page has its own URL; the guards here are for the user's
// benefit (no dead ends, no bouncing links). The API is what actually enforces access.
import { api, setUnauthorizedHandler } from "./api.js";
import { renderNav } from "./components/nav.js";
import { clear, h } from "./dom.js";
import { matchRoute } from "./lib/routes.js";

const PAGES = {
  login: () => import("./pages/login.js"),
  signup: () => import("./pages/signup.js"),
  visits: () => import("./pages/visits.js"),
  visit: () => import("./pages/visit.js"),
  users: () => import("./pages/users.js"),
  notfound: () => import("./pages/notfound.js"),
  noaccess: () => import("./pages/noaccess.js"),
};

let me; // undefined: not asked yet; null: signed out; object: signed in
let renderCount = 0;

export function currentPath() {
  return location.pathname + location.search;
}

export function loginUrl() {
  return `/login?next=${encodeURIComponent(currentPath())}`;
}

export async function loadMe({ force = false } = {}) {
  if (me === undefined || force) {
    try {
      me = await api("/api/me", { quiet401: true });
    } catch (e) {
      if (e.status !== 401) throw e;
      me = null;
    }
  }
  return me;
}

export function forgetMe() {
  me = undefined;
}

export function navigate(url, { replace = false } = {}) {
  history[replace ? "replaceState" : "pushState"]({}, "", url);
  render();
}

async function signOut() {
  try {
    await api("/api/auth/logout", { method: "POST", quiet401: true });
  } catch {
    /* already signed out */
  }
  me = null;
  navigate("/login");
}

export async function render() {
  const ticket = ++renderCount;
  const app = document.getElementById("app");
  const nav = document.getElementById("nav");
  const route = matchRoute(location.pathname);

  let user = null;
  let name = route ? route.name : "notfound";
  try {
    if (!route || route.access !== "public") user = await loadMe();
  } catch (e) {
    return showFatal(app, nav, e.message);
  }
  if (route && route.access !== "public" && !user) return navigate(loginUrl(), { replace: true });
  if (route && route.access === "admin" && user.role !== "admin") name = "noaccess";

  let title;
  let container;
  try {
    const page = await PAGES[name]();
    if (ticket !== renderCount) return; // a newer navigation started meanwhile
    renderNav(nav, user, { onSignOut: signOut });
    clear(app);
    container = h("div", { class: "wrap" });
    app.append(container);
    title = await page.render(container, { params: route ? route.params : {}, user, navigate, loadMe, forgetMe });
  } catch (e) {
    // Never leave a blank page: whatever failed, say so in words.
    if (ticket === renderCount) showFatal(app, nav, e.message);
    return;
  }
  if (ticket !== renderCount) return;
  document.title = title ? `${title} · Front Desk` : "Front Desk";
  const heading = container.querySelector("h1");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus({ preventScroll: true });
  }
}

function showFatal(app, nav, message) {
  clear(nav);
  clear(app);
  app.append(h("div", { class: "wrap" },
    h("h1", { class: "page-title" }, "Something went wrong"),
    h("wa-callout", { variant: "danger" }, message),
    h("p", {}, h("a", { href: currentPath() }, "Try again"))));
  document.title = "Something went wrong · Front Desk";
}

export function start() {
  setUnauthorizedHandler(() => {
    me = null;
    navigate(loginUrl(), { replace: true });
  });
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!link || event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (link.target || link.hasAttribute("download")) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname.startsWith("/api/") || url.pathname.startsWith("/static/")) return;
    event.preventDefault();
    if (url.pathname + url.search !== currentPath()) navigate(url.pathname + url.search);
  });
  window.addEventListener("popstate", render);
  render();
}
