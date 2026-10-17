import { h, clear } from "../dom.js";

// "People with access" is only offered to admins. That's a courtesy: the API refuses viewers either way.
export function renderNav(container, user, { onSignOut }) {
  clear(container);
  if (!user) return;
  const here = location.pathname;
  const link = (href, label, match) =>
    h("a", { href, "aria-current": match(here) ? "page" : null }, label);
  container.append(
    h("div", { class: "wrap nav" },
      h("a", { class: "wordmark", href: "/visits" }, "Front Desk"),
      h("nav", { class: "nav-links", "aria-label": "Main" },
        link("/visits", "Visits", (p) => p.startsWith("/visits")),
        user.role === "admin" ? link("/admin/users", "People with access", (p) => p === "/admin/users") : null,
      ),
      h("div", { class: "nav-user" },
        h("span", {}, user.name),
        h("span", { class: "role" }, user.role),
        h("button", { type: "button", class: "button-quiet", onclick: onSignOut }, "Sign out"),
      ),
    ),
  );
}
