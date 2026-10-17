import { api } from "../api.js";
import { h } from "../dom.js";
import { safeNext } from "../lib/safe-next.js";
import { authForm } from "./auth-form.js";

export async function render(container, { navigate, loadMe, forgetMe }) {
  const next = safeNext(new URLSearchParams(location.search).get("next"));
  if (await loadMe()) {
    navigate(next, { replace: true });
    return "Sign in";
  }
  container.append(authForm({
    title: "Sign in",
    intro: "See who visited the building, and when the lobby gets busy.",
    submitLabel: "Sign in",
    busyLabel: "Signing in…",
    autocomplete: "current-password",
    onSubmit: async (credentials) => {
      await api("/api/auth/login", { method: "POST", body: credentials, quiet401: true });
      forgetMe();
      navigate(next, { replace: true });
    },
    footer: h("p", { class: "aside" }, "New here? ",
      h("a", { href: `/signup?next=${encodeURIComponent(next)}` }, "Create an account")),
  }));
  return "Sign in";
}
