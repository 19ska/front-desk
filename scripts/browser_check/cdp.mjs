// A tiny headless-Chrome driver over the DevTools protocol. No npm packages:
// Node's built-in WebSocket and fetch are enough. Used by run.mjs to check the pages.
import { spawn } from "node:child_process";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function launch() {
  const profile = await mkdtemp(join(tmpdir(), "fd-chrome-"));
  const proc = spawn(CHROME, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--no-first-run", "--no-default-browser-check", "--hide-scrollbars", "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const wsUrl = await new Promise((resolve, reject) => {
    let buf = "";
    proc.stderr.on("data", (d) => {
      buf += d;
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) resolve(m[1]);
    });
    proc.on("exit", () => reject(new Error("Chrome exited before DevTools was ready")));
  });
  const port = new URL(wsUrl).port;
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = await connect(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  return {
    page,
    async close() {
      page.ws.close();
      proc.kill();
      await sleep(200);
      await rm(profile, { recursive: true, force: true });
    },
  };
}

async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let id = 0;
  const pending = new Map();
  const listeners = new Map();
  const errors = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method) {
      (listeners.get(msg.method) || []).forEach((fn) => fn(msg.params));
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    pending.set(++id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const on = (method, fn) => listeners.set(method, [...(listeners.get(method) || []), fn]);

  await send("Page.enable");
  await send("Runtime.enable");
  await send("Log.enable");
  on("Runtime.exceptionThrown", (p) => errors.push(p.exceptionDetails.exception?.description || p.exceptionDetails.text));
  on("Runtime.consoleAPICalled", (p) => { if (p.type === "error") errors.push(p.args.map((a) => a.value ?? a.description).join(" ")); });
  // Network 4xx entries are skipped: 401/403/404 are the access rules doing their job.
  on("Log.entryAdded", (p) => {
    if (p.entry.level === "error" && p.entry.source !== "network") errors.push(`${p.entry.text} ${p.entry.url || ""}`.trim());
  });

  let failing = null;
  on("Fetch.requestPaused", (p) => {
    if (failing && p.request.url.includes(failing.match)) {
      send("Fetch.fulfillRequest", { requestId: p.requestId, responseCode: failing.status,
        responseHeaders: [{ name: "content-type", value: "application/json" }],
        body: Buffer.from(JSON.stringify({ error: "Something went wrong on our side. Try again." })).toString("base64") });
    } else {
      send("Fetch.continueRequest", { requestId: p.requestId });
    }
  });

  const page = {
    ws,
    errors,
    // Make every request whose URL contains `match` answer with `status` (simulates a server failure).
    async failRequests(match, status) {
      failing = { match, status };
      await send("Fetch.enable", { patterns: [{ urlPattern: "*" }] });
    },
    async stopFailing() {
      failing = null;
      await send("Fetch.disable");
    },
    async setViewport(width, height = 900) {
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 600 });
    },
    async eval(expression) {
      const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    },
    async waitFor(expression, timeout = 8000) {
      const end = Date.now() + timeout;
      while (Date.now() < end) {
        if (await page.eval(`Boolean(${expression})`).catch(() => false)) return;
        await sleep(100);
      }
      throw new Error(`Timed out waiting for: ${expression}`);
    },
    async goto(url) {
      const loaded = new Promise((r) => on("Page.loadEventFired", r));
      await send("Page.navigate", { url });
      await loaded;
      await sleep(150);
    },
    // Wait until the router has rendered a page heading, no spinner is showing,
    // and every Web Awesome element on the page has loaded.
    async settled(timeout = 8000) {
      await page.waitFor(`document.querySelector('main h1') && !document.querySelector('main .loading') && !document.querySelector(':not(:defined)')`, timeout);
      await sleep(250);
    },
    async screenshot(path) {
      const { cssContentSize } = await send("Page.getLayoutMetrics");
      const { data } = await send("Page.captureScreenshot", {
        format: "png", captureBeyondViewport: true,
        clip: { x: 0, y: 0, width: cssContentSize.width, height: cssContentSize.height, scale: 1 },
      });
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, Buffer.from(data, "base64"));
    },
  };
  return page;
}
