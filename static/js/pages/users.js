// Admins only. The router shows viewers a no-access page, but the real refusal is the API's 403.
import { api } from "../api.js";
import { capital } from "../components/filters.js";
import { h } from "../dom.js";

export async function render(container) {
  container.append(h("div", { class: "loading" }, h("wa-spinner", {}), h("span", {}, "Loading people…")));
  let users;
  try {
    users = (await api("/api/admin/users")).users;
  } catch (e) {
    if (e.status === 401) return "People with access";
    container.replaceChildren(h("h1", { class: "page-title" }, "People with access"), h("wa-callout", { variant: "danger" }, e.message));
    return "People with access";
  }
  const joined = users.filter((u) => u.signed_up).length;
  container.replaceChildren(
    h("h1", { class: "page-title" }, "People with access"),
    h("p", { class: "lede" },
      `${users.length} ${users.length === 1 ? "person is" : "people are"} on the access list. `
      + `${joined} ${joined === 1 ? "has" : "have"} created an account.`),
    h("div", { class: "scroll-x stack-top" },
      h("table", { class: "visits" },
        h("thead", {}, h("tr", {}, ["Name", "Email", "Role", "Signed up"].map((x) => h("th", { scope: "col" }, x)))),
        h("tbody", {}, users.map((u) => h("tr", {},
          h("td", {}, u.name), h("td", {}, u.email), h("td", {}, capital(u.role)),
          h("td", {}, u.signed_up ? "Yes" : h("span", { class: "muted" }, "Not yet"))))))),
  );
  return "People with access";
}
