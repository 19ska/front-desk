// Shared layout for the sign-in and create-account pages.
import { h } from "../dom.js";

export function authForm({ title, intro, submitLabel, busyLabel, passwordHint, autocomplete, onSubmit, footer }) {
  const error = h("div", { role: "alert" });
  const button = h("button", { type: "submit", class: "button-primary" }, submitLabel);
  const form = h("form", { class: "form", novalidate: true },
    h("label", {}, "Email",
      h("input", { type: "email", name: "email", autocomplete: "email", required: true })),
    h("label", {}, "Password",
      h("input", { type: "password", name: "password", autocomplete, required: true }),
      passwordHint ? h("span", { class: "aside" }, passwordHint) : null),
    error,
    h("div", { class: "form-actions" }, button),
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    error.replaceChildren();
    button.disabled = true;
    button.textContent = busyLabel;
    try {
      await onSubmit({ email: String(data.get("email")), password: String(data.get("password")) });
    } catch (e) {
      error.replaceChildren(h("wa-callout", { variant: "danger" }, e.message));
      button.disabled = false;
      button.textContent = submitLabel;
    }
  });
  return h("div", { class: "auth" },
    h("a", { class: "wordmark", href: "/visits" }, "Front Desk"),
    h("h1", { class: "page-title" }, title),
    intro ? h("p", { class: "lede" }, intro) : null,
    h("div", { class: "stack" }, form, footer),
  );
}
