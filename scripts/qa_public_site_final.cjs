const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8765/";
const outDir = process.argv[3];
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: chromePath, headless: true });
  const errors = [];
  const checks = {};
  const downloads = {};
  try {
    const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const page = await desktop.newPage();
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
    await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForSelector(".result-card", { timeout: 10000 });
    checks.title = await page.title();
    checks.counts = { funding: await page.locator("#fundingCount").innerText(), resources: await page.locator("#resourceCount").innerText() };
    checks.desktopNoOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
    checks.duplicateIds = await page.evaluate(() => {
      const ids = [...document.querySelectorAll("[id]")].map((node) => node.id);
      return ids.filter((id, index) => ids.indexOf(id) !== index);
    });
    await page.selectOption("#stateSelect", { label: "Puerto Rico" });
    await page.locator("#topicOptions input").first().check();
    checks.puertoRicoMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
    await page.locator('[data-mode="Resource"]').click();
    checks.resourceMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
    checks.resourceCardsOnly = await page.locator(".result-card:not(.resource)").count() === 0;
    await page.locator('[data-mode="Both"]').click();
    await page.locator("#resetButton").click();
    const unfilteredMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
    await page.selectOption("#stageSelect", { label: "Construction" });
    checks.constructionMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
    checks.stageActuallyFilters = checks.constructionMatches > 0 && checks.constructionMatches < unfilteredMatches;
    await page.locator("#resetButton").click();
    await page.getByLabel("Local government").check();
    checks.localGovernmentMatches = Number((await page.locator("#matchCount").innerText()).replace(/,/g, ""));
    checks.applicantEligibilityFiltered = await page.locator(".result-card .details").evaluateAll((nodes) => nodes.filter((_, index) => index % 2 === 0).every((node) => /local government|municipal|county|city|town|village/i.test(node.textContent)));
    await page.locator("#resetButton").click();
    await page.selectOption("#stateSelect", { label: "American Samoa" });
    checks.territoryNationalCaution = await page.locator(".result-card").filter({ hasText: "confirm territory eligibility" }).count() > 0;

    const csvEvent = page.waitForEvent("download");
    await page.locator("#exportCsv").click();
    const csvDownload = await csvEvent;
    const csvPath = path.join(outDir, "community-export.csv");
    await csvDownload.saveAs(csvPath);
    downloads.csv = { bytes: fs.statSync(csvPath).size, rows: fs.readFileSync(csvPath, "utf8").split(/\r?\n/).filter(Boolean).length - 1 };

    const wordEvent = page.waitForEvent("download");
    await page.locator("#exportWord").click();
    const wordDownload = await wordEvent;
    const wordPath = path.join(outDir, "community-appendix.docx");
    await wordDownload.saveAs(wordPath);
    const wordBytes = fs.readFileSync(wordPath);
    downloads.word = {
      bytes: fs.statSync(wordPath).size,
      filename: wordDownload.suggestedFilename(),
      zipSignature: wordBytes[0] === 0x50 && wordBytes[1] === 0x4b,
    };
    checks.fullDownloads = {
      docx: (await page.request.get(`${baseUrl}downloads/RERC_Funding_and_Resource_Appendix_2026-07-14.docx`)).status(),
      xlsx: (await page.request.get(`${baseUrl}downloads/RERC_Funding_and_Resource_Master_2026-07-14.xlsx`)).status(),
    };
    await page.screenshot({ path: path.join(outDir, "desktop.png"), fullPage: true });
    await desktop.close();

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const mobilePage = await mobile.newPage();
    mobilePage.on("pageerror", (error) => errors.push(`mobile-pageerror:${error.message}`));
    await mobilePage.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
    await mobilePage.waitForSelector(".result-card", { timeout: 10000 });
    checks.mobileNoOverflow = await mobilePage.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
    checks.mobileControlsVisible = await mobilePage.locator("[data-mode]").evaluateAll((nodes) => nodes.every((node) => node.getBoundingClientRect().width > 0));
    await mobilePage.screenshot({ path: path.join(outDir, "mobile.png"), fullPage: true });
    await mobile.close();

    const failures = [];
    if (checks.counts.funding !== "659" || checks.counts.resources !== "61") failures.push("counts");
    if (!checks.desktopNoOverflow || !checks.mobileNoOverflow) failures.push("overflow");
    if (checks.duplicateIds.length) failures.push("duplicate_ids");
    if (checks.puertoRicoMatches < 1 || checks.resourceMatches < 1 || !checks.resourceCardsOnly) failures.push("filtering");
    if (!checks.stageActuallyFilters || checks.localGovernmentMatches < 1 || !checks.applicantEligibilityFiltered) failures.push("eligibility_controls");
    if (!checks.territoryNationalCaution) failures.push("territory_caution");
    if (downloads.csv.bytes < 100 || downloads.csv.rows < 1) failures.push("csv_export");
    if (downloads.word.bytes < 1000 || downloads.word.filename !== "RERC-community-appendix.docx" || !downloads.word.zipSignature) failures.push("word_export");
    if (checks.fullDownloads.docx !== 200 || checks.fullDownloads.xlsx !== 200) failures.push("downloads");
    if (!checks.mobileControlsVisible) failures.push("mobile_controls");
    if (errors.length) failures.push("browser_errors");
    const result = { status: failures.length ? "FAIL" : "PASS", baseUrl, checks, downloads, errors, failures };
    fs.writeFileSync(path.join(outDir, "playwright_qa.json"), JSON.stringify(result, null, 2));
    process.stdout.write(JSON.stringify(result, null, 2));
    process.exitCode = failures.length ? 1 : 0;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(error.stack || String(error));
  process.exitCode = 1;
});
