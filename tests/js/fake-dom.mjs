// Just enough of `document` to test dom.js without a browser or any npm package.
class FakeText {
  constructor(text) { this.nodeType = 3; this.textContent = text; }
}

class FakeElement {
  constructor(tag) {
    this.nodeType = 1;
    this.tagName = tag.toUpperCase();
    this.attributes = {};
    this.children = [];
    this.listeners = {};
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  append(...nodes) { this.children.push(...nodes); }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  get textContent() { return this.children.map((c) => c.textContent).join(""); }
}

export function makeFakeDocument() {
  return {
    createElement: (tag) => new FakeElement(tag),
    createTextNode: (text) => new FakeText(text),
  };
}
