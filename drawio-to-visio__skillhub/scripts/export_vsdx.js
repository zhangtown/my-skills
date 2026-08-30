#!/usr/bin/env node
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

function fatal(message) {
  process.stderr.write(`ERROR: ${message}\n`);
  process.exit(1);
}

function isExecutable(candidate) {
  if (!candidate) return false;
  try {
    if (!fs.statSync(candidate).isFile()) return false;
    fs.accessSync(candidate, process.platform === "win32" ? fs.constants.F_OK : fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function joinIfBase(base, ...parts) {
  return base ? path.join(base, ...parts) : undefined;
}

function findBrowser() {
  let playwrightBrowser;
  try {
    playwrightBrowser = chromium.executablePath();
  } catch {
    playwrightBrowser = undefined;
  }

  const candidates = [
    process.env.DRAWIO_VISIO_BROWSER,
    playwrightBrowser,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
    "/usr/bin/microsoft-edge-stable",
    joinIfBase(process.env.PROGRAMFILES, "Google/Chrome/Application/chrome.exe"),
    joinIfBase(process.env.PROGRAMFILES, "Microsoft/Edge/Application/msedge.exe"),
    joinIfBase(process.env["PROGRAMFILES(X86)"], "Microsoft/Edge/Application/msedge.exe"),
    joinIfBase(process.env.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"),
  ].filter(Boolean);

  const executableNames = process.platform === "win32"
    ? ["chrome.exe", "msedge.exe"]
    : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"];
  for (const directory of (process.env.PATH || "").split(path.delimiter).filter(Boolean)) {
    for (const executable of executableNames) candidates.push(path.join(directory, executable));
  }

  const cacheRoots = [
    process.env.PLAYWRIGHT_BROWSERS_PATH && process.env.PLAYWRIGHT_BROWSERS_PATH !== "0"
      ? path.resolve(process.env.PLAYWRIGHT_BROWSERS_PATH)
      : undefined,
    joinIfBase(process.env.HOME, "Library/Caches/ms-playwright"),
    joinIfBase(process.env.HOME, ".cache/ms-playwright"),
    joinIfBase(process.env.LOCALAPPDATA, "ms-playwright"),
  ].filter(Boolean);

  for (const root of cacheRoots) {
    if (!fs.existsSync(root)) continue;
    const entries = fs.readdirSync(root).sort((left, right) => {
      const leftVersion = Number(left.match(/(\d+)$/)?.[1] || 0);
      const rightVersion = Number(right.match(/(\d+)$/)?.[1] || 0);
      return rightVersion - leftVersion;
    });
    for (const entry of entries) {
      const base = path.join(root, entry);
      candidates.push(
        path.join(base, "chrome-headless-shell-mac-arm64/chrome-headless-shell"),
        path.join(base, "chrome-headless-shell-mac-x64/chrome-headless-shell"),
        path.join(base, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        path.join(base, "chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        path.join(base, "chrome-linux/chrome"),
        path.join(base, "chrome-linux64/chrome"),
        path.join(base, "chrome-headless-shell-linux64/chrome-headless-shell"),
        path.join(base, "chrome-win/chrome.exe"),
        path.join(base, "chrome-win64/chrome.exe"),
        path.join(base, "chrome-headless-shell-win64/chrome-headless-shell.exe")
      );
    }
  }

  return [...new Set(candidates)].find(isExecutable);
}

function contentType(file) {
  const types = {
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".xml": "application/xml; charset=utf-8",
  };
  return types[path.extname(file).toLowerCase()] || "application/octet-stream";
}

async function main() {
  const [inputArg, outputArg, webrootArg, timeoutArg] = process.argv.slice(2);
  if (!inputArg || !outputArg || !webrootArg) {
    fatal("usage: export_vsdx.js INPUT OUTPUT DRAWIO_WEBROOT [TIMEOUT_SECONDS]");
  }

  const input = path.resolve(inputArg);
  const output = path.resolve(outputArg);
  const webroot = path.resolve(webrootArg);
  const timeoutSeconds = Number(timeoutArg || 180);
  if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 30) {
    fatal("timeout must be an integer of at least 30 seconds");
  }
  const timeoutMs = timeoutSeconds * 1000;
  const browserPath = findBrowser();

  if (!fs.existsSync(input)) fatal(`input not found: ${input}`);
  if (!fs.existsSync(path.join(webroot, "index.html"))) fatal(`invalid diagrams.net webroot: ${webroot}`);
  if (!browserPath) fatal("no compatible Chromium, Chrome, or Edge executable found");

  const source = fs.readFileSync(input, "utf8");
  if (!source.includes("<mxfile") && !source.includes("<mxGraphModel")) {
    fatal("input does not look like Draw.io XML");
  }

  const server = http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");

    if (url.pathname === "/__input__.drawio") {
      response.writeHead(200, { "content-type": "application/xml; charset=utf-8" });
      response.end(source);
      return;
    }
    if (url.pathname === "/notifications") {
      response.writeHead(204);
      response.end();
      return;
    }

    const relative = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
    const target = path.normalize(path.join(webroot, relative));

    if (!target.startsWith(webroot + path.sep) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) {
      response.writeHead(404);
      response.end("not found");
      return;
    }

    response.writeHead(200, { "content-type": contentType(target) });
    fs.createReadStream(target).pipe(response);
  });

  let browser;
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    const port = server.address().port;
    const inputUrl = `http://127.0.0.1:${port}/__input__.drawio`;
    const appUrl = `http://127.0.0.1:${port}/index.html?local=1&lang=en&ui=kennedy&url=${encodeURIComponent(inputUrl)}`;
    const localOrigin = new URL(appUrl).origin;

    browser = await chromium.launch({
      executablePath: browserPath,
      headless: true,
      args: ["--disable-dev-shm-usage"],
    });
    const context = await browser.newContext({
      acceptDownloads: true,
      serviceWorkers: "block",
    });

    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin === localOrigin) {
        await route.continue();
      } else if (url.pathname.endsWith("/js/extensions.min.js")) {
        await route.fulfill({
          path: path.join(webroot, "js/extensions.min.js"),
          contentType: "text/javascript; charset=utf-8",
        });
      } else {
        await route.abort("blockedbyclient");
      }
    });
    await context.routeWebSocket("**/*", async (webSocket) => {
      await webSocket.close({ code: 1008, reason: "WebSockets are disabled for local conversion" });
    });

    const page = await context.newPage();
    page.setDefaultTimeout(timeoutMs);
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));

    process.stdout.write("[1/6] Loading local diagrams.net editor\n");
    await page.goto(appUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    await page.getByText("File", { exact: true }).first().waitFor();
    await page.waitForFunction(
      () => document.title.includes("__input__.drawio") && document.body.innerText.length > 100,
      null,
      { timeout: timeoutMs }
    );
    process.stdout.write("[2/6] Draw.io diagram loaded\n");

    process.stdout.write("[3/6] Local-only browser routing enabled\n");

    await page.getByText("File", { exact: true }).first().click();
    await page.getByText("Export as", { exact: true }).last().hover();
    await page.getByText("VSDX (beta)...", { exact: true }).last().click();
    process.stdout.write("[4/6] VSDX export requested\n");

    await page.waitForFunction(() => {
      const text = document.body.innerText;
      const visibleExport = [...document.querySelectorAll("button")].some(
        (button) => button.offsetParent !== null && button.textContent.trim() === "Export"
      );
      return text.includes("Save As:") || visibleExport;
    }, null, { timeout: timeoutMs });

    const exportButton = page.getByText("Export", { exact: true }).last();
    if (await exportButton.isVisible().catch(() => false)) await exportButton.click();

    await page.getByText("Save As:", { exact: true }).waitFor({ timeout: timeoutMs });
    process.stdout.write("[5/6] VSDX generated; selecting local download\n");
    const downloadPromise = page.waitForEvent("download", { timeout: timeoutMs });
    await page.locator("select:visible").last().selectOption("download");
    await page.getByText("OK", { exact: true }).last().click();
    const download = await downloadPromise;

    fs.mkdirSync(path.dirname(output), { recursive: true });
    await download.saveAs(output);
    process.stdout.write("[6/6] Download captured\n");

    if (pageErrors.length) {
      process.stderr.write(`WARNING: page errors observed: ${pageErrors.join(" | ")}\n`);
    }
    process.stdout.write(`Exported ${input} -> ${output}\n`);
  } finally {
    if (browser) await browser.close().catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => fatal(error.stack || error.message || String(error)));
