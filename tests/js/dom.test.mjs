import { test } from "node:test";
import assert from "node:assert/strict";
import { makeFakeDocument } from "./fake-dom.mjs";

globalThis.document = makeFakeDocument();
const { h } = await import("../../static/js/dom.js");

test("h puts untrusted text in text nodes, never markup", () => {
  const el = h("td", {}, "<img src=x onerror=alert(1)>");
  assert.equal(el.children[0].nodeType, 3);
  assert.equal(el.children[0].textContent, "<img src=x onerror=alert(1)>");
});

test("h sets class, href and listeners", () => {
  let clicked = false;
  const a = h("a", { class: "row", href: "/visits/V1", onclick: () => { clicked = true; } }, "Open");
  assert.equal(a.attributes.class, "row");
  assert.equal(a.attributes.href, "/visits/V1");
  a.listeners.click();
  assert.equal(clicked, true);
});
