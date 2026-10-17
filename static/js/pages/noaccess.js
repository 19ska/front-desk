import { h } from "../dom.js";

export async function render(container) {
  container.append(
    h("h1", { class: "page-title" }, "You don't have access to this page"),
    h("p", {}, "Only admins can see who has access to the app."),
    h("p", {}, h("a", { href: "/visits" }, "Go to visits")),
  );
  return "No access";
}
