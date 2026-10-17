import { h } from "../dom.js";

export async function render(container) {
  container.append(
    h("h1", { class: "page-title" }, "Page not found"),
    h("p", {}, "There's nothing at ", h("code", {}, location.pathname), "."),
    h("p", {}, h("a", { href: "/visits" }, "Go to visits")),
  );
  return "Page not found";
}
