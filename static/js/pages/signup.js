import { api } from "../api.js";
import { h } from "../dom.js";
import { safeNext } from "../lib/safe-next.js";
import { authForm } from "./auth-form.js";

export async function render(container, { navigate, forgetMe }) {
  const next = safeNext(new URLSearchParams(location.search).get("next"));
  container.append(authForm({
    title: "Create an account",
    intro: "Use your work email. Only people on the access list can create an account.",
    submitLabel: "Create account",
    busyLabel: "Creating account…",
    passwordHint: "At least 8 characters.",
    autocomplete: "new-password",
    onSubmit: async (credentials) => {
      await api("/api/auth/signup", { method: "POST", body: credentials, quiet401: true });
      await api("/api/auth/login", { method: "POST", body: credentials, quiet401: true });
      forgetMe();
      navigate(next, { replace: true });
    },
    footer: h("p", { class: "aside" }, "Already have an account? ",
      h("a", { href: `/login?next=${encodeURIComponent(next)}` }, "Sign in")),
  }));
  return "Create an account";
}
