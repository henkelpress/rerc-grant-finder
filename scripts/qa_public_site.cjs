const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8765/";
const outDir = process.argv[3];
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: chromePath, headless: true });
  const errors = [];
  const checks = {};
  const downloads = {};

  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const page = await desktop.newPage();
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  checks.title = await page.title();
  checks.catalogCounts = {
    funding: await page.locator("#fundingCount").innerText(),
    resources: await page.locator("#resourceCount").innerText(),
  };
  checks.initialMatches = await page.locator("#matchCount").innerText();
  checks.desktopNoHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
  checks.duplicateIds = await page.evaluate(() => {
    const ids = [...document.querySelectorAll("[id]")].map((node) => node.id);
    return ids.filter((id, index) => ids.indexOf(id) !== index);
  });

  await page.selectOption("#stateSelect", { label: "Puerto Rico" });
  await page.locator("#topicOptions input").first().check();
  await page.waitForTimeout(150);
  checks.puertoRicoMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
  await page.locator('[data-mode="Resource"]').click();
  await page.waitForTimeout(150);
  checks.resourceModeMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
  checks.resourceCardsOnly = await page.locator(".result-card:not(.resource)").count() === 0;

  await page.locator('[data-mode="Both"]').click();
  const csvPromise = page.waitForEvent("download");
  await page.locator("#exportCsv").click();
  const csvDownload = await csvPromise;
  const csvPath = path.join(outDir, "community-export.csv");
  await csvDownload.saveAs(csvPath);
  const csvText = fs.readFileSync(csvPath, "utf8");
  downloads.csv = { bytes: fs.statSync(csvPath).size, rows: csvText.split(/\r?\n/).filter(Boolean).length - 1 };

  const wordPromise = page.waitForEvent("download");
  await page.locator("#exportWord").click();
  const wordDownload = await wordPromise;
  const wordPath = path.join(outDir, "community-appendix.docx");
  await wordDownload.saveAs(wordPath);
  const wordBytes = fs.readFileSync(wordPath);
  downloads.word = {
      bytes: fs.statSync(wordPath).size,
      filename: wordDownload.suggestedFilename(),
      zipSignature: wordBytes[0] === 0x50 && wordBytes[1] === 0x4b,
    };

  const fullDocx = await page.request.get(`${baseUrl}downloads/RERC_Funding_and_Resource_Appendix_2026-07-13.docx`);
  const fullXlsx = await page.request.get(`${baseUrl}downloads/RERC_Funding_and_Resource_Master_2026-07-13.xlsx`);
  checks.fullDownloads = { docx: fullDocx.status(), xlsx: fullXlsx.status() };
  await page.screenshot({ path: path.join(outDir, "desktop.png"), fullPage: true });
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mobilePage = await mobile.newPage();
  mobilePage.on("pageerror", (error) => errors.push(`mobile-pageerror:${error.message}`));
  mobilePage.on("console", (message) => { if (message.type() === "error") errors.push(`mobile-console:${message.text()}`); });
  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  checks.mobileNoHorizontalOverflow = await mobilePage.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
  checks.mobileModeButtonsVisible = await mobilePage.locator("[data-mode]").evaluateAll((nodes) => nodes.every((node) => {
    const rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }));
  await mobilePage.screenshot({ path: path.join(outDir, "mobile.png"), fullPage: true });
  await mobile.close();
  await browser.close();

  const failures = [];
  if (checks.catalogCounts.funding !== "653" || checks.catalogCounts.resources !== "65") failures.push("catalog_counts");
  if (!checks.desktopNoHorizontalOverflow || !checks.mobileNoHorizontalOverflow) failures.push("horizontal_overflow");
  if (checks.duplicateIds.length) failures.push("duplicate_ids");
  if (checks.puertoRicoMatches < 1 || checks.resourceModeMatches < 1 || !checks.resourceCardsOnly) failures.push("filtering");
  if (downloads.csv.bytes < 100 || downloads.csv.rows < 1) failures.push("csv_export");
    if (downloads.word.bytes < 1000 || downloads.word.filename !== "RERC-community-appendix.docx" || !downloads.word.zipSignature) failures.push("word_export");
  if (checks.fullDownloads.docx !== 200 || checks.fullDownloads.xlsx !== 200) failures.push("full_downloads");
  if (!checks.mobileModeButtonsVisible) failures.push("mobile_controls");
  if (errors.length) failures.push("browser_errors");
  const result = { status: failures.length ? "FAIL" : "PASS", baseUrl, checks, downloads, errors, failures };
  fs.writeFileSync(path.join(outDir, "playwright_qa.json"), JSON.stringify(result, null, 2));
  process.stdout.write(JSON.stringify(result, null, 2));
  process.exitCode = failures.length ? 1 : 0;
}

run().catch((error) => {
  process.stderr.write(error.stack || String(error));
  process.exitCode = 1;
});
