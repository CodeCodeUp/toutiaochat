const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const REPO_ROOT = path.resolve(__dirname, "..", "..", "..", "..", "..");
const SKILL_ROOT = path.join(
  REPO_ROOT,
  ".agents",
  "skills",
  "toutiao-content-workflow"
);
const PROFILE_DIR = path.join(SKILL_ROOT, "browser-profile", "chrome");
const RUNTIME_ROOT = path.join(SKILL_ROOT, "runtime");
const FLOW_OUTPUT_ROOT = path.join(RUNTIME_ROOT, "flow-images");
const FLOW_CRAWL_ROOT = path.join(RUNTIME_ROOT, "flow-crawl");
const FLOW_URL =
  "https://labs.google/fx/zh/tools/flow/project/354a1f5c-6935-4e53-9cde-8efe14b8349b";

const DEFAULT_PROMPT =
  "A yellow banana on a minimal studio background, photorealistic, soft light.";
const DEFAULT_TIMEOUT_SECONDS = 600;
const DEFAULT_EXPECTED_COUNT = 1;

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function timestampForPath(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(
    date.getHours()
  )}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

function parseArgs(argv) {
  const args = {
    prompt: DEFAULT_PROMPT,
    timeoutSeconds: DEFAULT_TIMEOUT_SECONDS,
    expectedCount: DEFAULT_EXPECTED_COUNT,
    outputDir: FLOW_OUTPUT_ROOT,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === "--prompt" && next) {
      args.prompt = next;
      index += 1;
      continue;
    }
    if (token === "--timeout-seconds" && next) {
      args.timeoutSeconds = Number.parseInt(next, 10) || DEFAULT_TIMEOUT_SECONDS;
      index += 1;
      continue;
    }
    if (token === "--expected-count" && next) {
      args.expectedCount = Number.parseInt(next, 10) || DEFAULT_EXPECTED_COUNT;
      index += 1;
      continue;
    }
    if (token === "--output-dir" && next) {
      args.outputDir = path.resolve(process.cwd(), next);
      index += 1;
      continue;
    }
    if (token === "--help" || token === "-h") {
      printHelpAndExit(0);
    }
  }

  return args;
}

function printHelpAndExit(code) {
  console.log("Usage: node generate_flow_images.js [options]");
  console.log("");
  console.log("Options:");
  console.log("  --prompt <text>            Prompt to send to Google Flow.");
  console.log(
    `  --timeout-seconds <n>      Wait timeout in seconds. Default: ${DEFAULT_TIMEOUT_SECONDS}.`
  );
  console.log(
    `  --expected-count <n>       Minimum number of newly generated images. Default: ${DEFAULT_EXPECTED_COUNT}.`
  );
  console.log(
    "  --output-dir <path>        Directory for downloaded files. Default: skill runtime/flow-images."
  );
  process.exit(code);
}

function extFromContentType(contentType) {
  const normalized = (contentType || "").toLowerCase();
  if (normalized.includes("image/jpeg")) {
    return ".jpg";
  }
  if (normalized.includes("image/png")) {
    return ".png";
  }
  if (normalized.includes("image/webp")) {
    return ".webp";
  }
  return ".bin";
}

function buildMediaUrl(name) {
  return `https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name=${name}`;
}

function collectHistoricalMediaNames(rootDir) {
  const known = new Set();
  if (!fs.existsSync(rootDir)) {
    return known;
  }

  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
        continue;
      }
      if (!entry.isFile() || entry.name !== "result.json") {
        continue;
      }
      try {
        const payload = JSON.parse(fs.readFileSync(fullPath, "utf-8"));
        const savedFiles = Array.isArray(payload.savedFiles) ? payload.savedFiles : [];
        for (const item of savedFiles) {
          const mediaName = String(item.mediaName || item.media_name || "").trim();
          if (mediaName) {
            known.add(mediaName);
          }
        }
      } catch (_error) {
        continue;
      }
    }
  };

  walk(rootDir);
  return known;
}

async function dismissCookieBanner(page) {
  const acceptButton = page.locator("button", { hasText: "OK, got it" });
  if (await acceptButton.count()) {
    const button = acceptButton.first();
    if (await button.isVisible().catch(() => false)) {
      await button.click();
      await page.waitForTimeout(750);
    }
  }
}

async function waitForEditor(page) {
  const editor = page.locator('[contenteditable="true"][role="textbox"]').last();
  await editor.waitFor({ state: "visible", timeout: 120000 });
  return editor;
}

async function writePrompt(page, editor, prompt) {
  await editor.click({ force: true });
  await page.waitForTimeout(300);
  await page.keyboard.press(process.platform === "win32" ? "Control+A" : "Meta+A");
  await page.keyboard.press("Backspace");
  await page.waitForTimeout(200);
  await page.keyboard.type(prompt, { delay: 35 });
  await page.waitForTimeout(800);

  const text = await editor.evaluate((element) => (element.innerText || "").trim());
  if (text !== prompt) {
    await editor.evaluate((element, value) => {
      const textNode = document.createTextNode(value);
      element.innerHTML = "";
      const paragraph = document.createElement("p");
      paragraph.appendChild(textNode);
      element.appendChild(paragraph);
      element.dispatchEvent(new InputEvent("input", { bubbles: true, data: value }));
    }, prompt);
    await page.waitForTimeout(400);
  }
}

async function collectFlowState(page) {
  return await page.evaluate(() => {
    const extractMediaName = (value) => {
      if (!value) {
        return null;
      }
      try {
        const url = new URL(value, location.href);
        return url.searchParams.get("name");
      } catch (_error) {
        return null;
      }
    };

    const images = Array.from(
      document.querySelectorAll('img[src*="/fx/api/trpc/media.getMediaUrlRedirect?name="]')
    ).map((image) => {
      const rect = image.getBoundingClientRect();
      const src = image.getAttribute("src");
      return {
        alt: image.getAttribute("alt"),
        src,
        name: extractMediaName(src),
        width: rect.width,
        height: rect.height,
        x: rect.x,
        y: rect.y,
      };
    });

    const buttons = Array.from(document.querySelectorAll("button")).map((button) => {
      const rect = button.getBoundingClientRect();
      return {
        text: (button.innerText || "").trim(),
        ariaLabel: button.getAttribute("aria-label"),
        className: button.className,
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      };
    });

    return {
      url: location.href,
      title: document.title,
      bodyText: (document.body.innerText || "").slice(0, 8000),
      images,
      buttons,
      uniqueMediaNames: [...new Set(images.map((image) => image.name).filter(Boolean))],
    };
  });
}

async function clickCreate(page) {
  const createButton = page.locator("button").filter({ hasText: "arrow_forward" }).last();
  await createButton.waitFor({ state: "visible", timeout: 120000 });
  await createButton.click();
}

async function waitForNewMedia(page, baselineNames, historicalNames, expectedCount, timeoutSeconds) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  let lastState = await collectFlowState(page);

  while (Date.now() < deadline) {
    await page.waitForTimeout(3000);
    lastState = await collectFlowState(page);
    const newNames = lastState.uniqueMediaNames.filter(
      (name) => !baselineNames.has(name) && !historicalNames.has(name)
    );
    if (newNames.length >= expectedCount) {
      return { newNames, state: lastState };
    }
  }

  const observedNames = lastState.uniqueMediaNames.filter(
    (name) => !baselineNames.has(name) && !historicalNames.has(name)
  );
  throw new Error(
    `Timed out after ${timeoutSeconds}s waiting for ${expectedCount} new image(s). Observed ${observedNames.length}.`
  );
}

async function downloadMedia(context, mediaNames, downloadDir) {
  const savedFiles = [];

  for (let index = 0; index < mediaNames.length; index += 1) {
    const mediaName = mediaNames[index];
    const url = buildMediaUrl(mediaName);
    const response = await context.request.get(url, {
      headers: { referer: FLOW_URL },
    });

    if (!response.ok()) {
      throw new Error(`Failed to download ${mediaName}: HTTP ${response.status()}`);
    }

    const contentType = response.headers()["content-type"] || "";
    const ext = extFromContentType(contentType);
    const fileName = `${String(index + 1).padStart(2, "0")}_${mediaName}${ext}`;
    const filePath = path.join(downloadDir, fileName);
    fs.writeFileSync(filePath, await response.body());

    savedFiles.push({
      mediaName,
      url: response.url(),
      fileName,
      filePath,
      contentType,
      sizeBytes: fs.statSync(filePath).size,
    });
  }

  return savedFiles;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  ensureDir(args.outputDir);
  ensureDir(FLOW_CRAWL_ROOT);

  const runStamp = timestampForPath();
  const runDir = path.join(args.outputDir, runStamp);
  ensureDir(runDir);

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: "chrome",
    headless: false,
    viewport: { width: 1440, height: 960 },
    acceptDownloads: true,
    locale: "zh-CN",
    ignoreDefaultArgs: ["--enable-automation"],
    args: [
      "--disable-blink-features=AutomationControlled",
      "--disable-infobars",
      "--start-maximized",
    ],
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    Object.defineProperty(navigator, "languages", {
      get: () => ["zh-CN", "zh", "en-US", "en"],
    });
    Object.defineProperty(navigator, "plugins", {
      get: () => [1, 2, 3, 4, 5],
    });
    window.chrome = window.chrome || { runtime: {} };
  });

  const page = context.pages()[0] || (await context.newPage());

  try {
    await page.goto(FLOW_URL, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await page.waitForTimeout(6000);
    await dismissCookieBanner(page);

    const editor = await waitForEditor(page);
    const baselineState = await collectFlowState(page);
    const baselineNames = new Set(baselineState.uniqueMediaNames);
    const historicalNames = collectHistoricalMediaNames(FLOW_OUTPUT_ROOT);

    await writePrompt(page, editor, args.prompt);
    await clickCreate(page);

    const { newNames, state: finalState } = await waitForNewMedia(
      page,
      baselineNames,
      historicalNames,
      args.expectedCount,
      args.timeoutSeconds
    );
    const selectedNames = newNames.slice(0, args.expectedCount);

    await page.screenshot({
      path: path.join(runDir, "after-generation.png"),
      fullPage: true,
    });

    const savedFiles = await downloadMedia(context, selectedNames, runDir);
    const metadata = {
      prompt: args.prompt,
      flowUrl: FLOW_URL,
      runStamp,
      expectedCount: args.expectedCount,
      timeoutSeconds: args.timeoutSeconds,
      baselineMediaNames: baselineState.uniqueMediaNames,
      newMediaNames: selectedNames,
      observedNewMediaNames: newNames,
      savedFiles,
      finalUrl: finalState.url,
      finalTitle: finalState.title,
      bodyTextSnippet: finalState.bodyText.slice(0, 2000),
      createdAt: new Date().toISOString(),
    };

    fs.writeFileSync(
      path.join(runDir, "result.json"),
      JSON.stringify(metadata, null, 2),
      "utf-8"
    );
    fs.writeFileSync(
      path.join(FLOW_CRAWL_ROOT, "latest-flow-generation.json"),
      JSON.stringify(metadata, null, 2),
      "utf-8"
    );

    console.log(`RUN_DIR=${runDir}`);
    for (const file of savedFiles) {
      console.log(`DOWNLOADED=${file.filePath}`);
    }
    console.log(`RESULT_JSON=${path.join(runDir, "result.json")}`);
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
