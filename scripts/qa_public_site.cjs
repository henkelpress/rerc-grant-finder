const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const baseUrl = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3] || "browser-qa";
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const checks = {}, downloads = {}, errors = [], failures = [];
const check = (name, ok) => { if (!ok) failures.push(name); };
const hasSensitiveKey = (value) => {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(hasSensitiveKey);
  return Object.entries(value).some(([key, nested]) => /^(token|api[_-]?key|secret)$/i.test(key) || hasSensitiveKey(nested));
};
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
async function download(page, selector, filename) {
  console.log("QA download: " + selector);
  const event = page.waitForEvent("download"); await page.locator(selector).click();
  const item = await event, file = path.join(outDir, filename); await item.saveAs(file);
  return { file, name: item.suggestedFilename(), bytes: fs.statSync(file).size };
}
async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(fs.existsSync(chromePath) ? { executablePath: chromePath, headless: true } : { headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => { if (message.type() === "error") { const where = message.location(); errors.push(`console:${where.url}:${where.lineNumber}:${where.columnNumber}:${message.text()}`); } });
    await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("html.rerc-planner-ready"); await page.waitForSelector(".result-card");
    checks.counts = await page.evaluate(() => ["fundingCount", "resourceCount", "caseStudyCount"].map((id) => Number(document.getElementById(id).textContent)));
    check("counts", checks.counts.join(",") === "659,61,476" && checks.counts.reduce((sum, value) => sum + value, 0) === 1196);
    checks.desktopNoOverflow = await overflow(page); check("desktop_overflow", checks.desktopNoOverflow);
    const modes = { modeAll: '[data-mode="All"]', modeFunding: "#showFunding", modeResources: "#showResources", modeCases: "#showCases" };
    checks.modes = {}; for (const [name, selector] of Object.entries(modes)) { await page.locator(selector).click(); checks.modes[name] = await page.locator(selector).getAttribute("aria-pressed") === "true"; }
    check("mode_buttons", Object.values(checks.modes).every(Boolean));
    await page.locator("#showFunding").click();
    const datedTitle = await page.evaluate(() => (window.RERCExplorer.catalog || []).find((item) => { const date = item.item_type === "Funding" ? window.RERCExplorer.parseDeadline(item) : null; return date instanceof Date && !Number.isNaN(date.getTime()) && date.getTime() >= new Date().setHours(0, 0, 0, 0); })?.title || "");
    if (datedTitle) { await page.evaluate((title) => { const input = document.getElementById("keywordSearch"); input.value = title; input.dispatchEvent(new Event("input", { bubbles: true })); }, datedTitle); await page.waitForTimeout(250); }
    const firstSave = page.locator('[data-action="planner-save"]').first(); await firstSave.click(); await page.waitForTimeout(500);
    checks.savedBeforeReload = Number(await page.evaluate(() => document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0));
    await page.reload({ waitUntil: "networkidle" }); await page.waitForSelector("html.rerc-planner-ready");
    checks.savedAfterReload = Number(await page.evaluate(() => document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0)); check("saved_persists", checks.savedBeforeReload === 1 && checks.savedAfterReload === 1);
    await page.locator('[data-mode="All"]').click();
    for (let index = 0; index < 3; index += 1) {
      const save = page.locator('[data-action="planner-save"][aria-pressed="false"]').first();
      if (await save.count()) { await save.click(); await page.waitForTimeout(100); }
    }
    for (let index = 0; index < 4; index += 1) {
      const compare = page.locator('[data-action="planner-compare"][aria-pressed="false"]').first();
      if (await compare.count()) { await compare.click(); await page.waitForTimeout(100); }
    }    checks.compare = Number(await page.evaluate(() => document.querySelector("#compareCountBadge")?.textContent || 0)); check("compare_max_three", checks.compare === 3);
    await page.locator("#openLanguage").click(); await page.locator("#languageDialog").waitFor({ state: "visible" });
    const spanishOption = page.locator('#languageDialog input[value="es"]');
    checks.spanishDialog = await spanishOption.count() === 1 && /Espa/.test(await page.locator("#languageDialog").innerText()); check("spanish_dialog", checks.spanishDialog);
    await spanishOption.click(); await page.locator("#languageDialog").waitFor({ state: "hidden" }); await page.waitForTimeout(50);
    checks.spanishApplied = await page.locator("html").getAttribute("lang") === "es" && /Espa/.test(await page.locator("#openLanguage span").innerText()) && await page.evaluate(() => document.activeElement?.id === "openLanguage"); check("spanish_applied", checks.spanishApplied);
    await page.locator("#openLanguage").click(); await page.locator('#languageDialog input[value="en"]').click(); await page.locator("#languageDialog").waitFor({ state: "hidden" });
    checks.englishRestored = await page.locator("html").getAttribute("lang") === "en"; check("english_restored", checks.englishRestored);
    checks.roadmapPhases = await page.locator("#roadmap select").first().locator("option").allTextContents(); check("roadmap_phases", ["Plan", "Design", "Build", "Operate"].every((phase) => checks.roadmapPhases.includes(phase)));
    await page.locator("#projectTitle").fill("Private title"); await page.locator("#projectNotes").fill("Private notes"); await page.locator("#shareWorkspace").click();
    const share = await page.locator("#shareLink").inputValue(), fragment = share.split("#")[1] || "";
    checks.share = { length: fragment.length, private: !share.includes("projectTitle") && !share.includes("projectNotes") }; check("share_link", checks.share.length <= 1800 && checks.share.private);
    await page.locator("#shareDialog button[value=close]").click();
    downloads.csv = await download(page, "#exportPlanCsv", "plan.csv"); downloads.docx = await download(page, "#exportPlanWord", "plan.docx"); downloads.ics = await download(page, "#exportCalendar", "plan.ics"); downloads.workspace = await download(page, "#exportWorkspaceFile", "plan.rerc-workspace");
    page.once("dialog", (dialog) => dialog.accept()); downloads.rercie = await download(page, "#exportRercie", "plan.rercie");
    checks.rercie = JSON.parse(fs.readFileSync(downloads.rercie.file, "utf8")); check("download_events", Object.values(downloads).every((item) => item.bytes > 0));
    check("rercie_schema", checks.rercie.schema === "rercie-handoff" && checks.rercie.version === 1 && !hasSensitiveKey(checks.rercie) && !/sk-[A-Za-z0-9]{12,}/.test(JSON.stringify(checks.rercie)));
    await page.screenshot({ path: path.join(outDir, "desktop.png"), fullPage: true }); await context.close();
    checks.mobile = {}; for (const width of [320, 390]) {
      const mobile = await browser.newContext({ viewport: { width, height: 844 } }); const page = await mobile.newPage(); page.on("pageerror", (error) => errors.push(`mobile:${error.message}`));
      await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 }); await page.waitForSelector("html.rerc-planner-ready");
      const controls = await page.locator("button, a, input, select").evaluateAll((nodes) => nodes.filter((node) => { const style = getComputedStyle(node), box = node.getBoundingClientRect(); return !node.matches('input[type="file"]') && style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0; }).map((node) => Math.min(node.getBoundingClientRect().width, node.getBoundingClientRect().height)));
      checks.mobile[width] = { overflow: await overflow(page), bottomNav: await page.locator(".mobile-nav").isVisible(), controls44: controls.every((value) => value >= 44) }; check(`mobile_${width}`, Object.values(checks.mobile[width]).every(Boolean));
      await page.screenshot({ path: path.join(outDir, `mobile-${width}.png`), fullPage: true }); await mobile.close();
    }
    check("browser_errors", errors.length === 0);
  } finally { await browser.close(); }
  const report = { status: failures.length ? "FAIL" : "PASS", baseUrl, checks, downloads: Object.fromEntries(Object.entries(downloads).map(([name, item]) => [name, { name: item.name, bytes: item.bytes }])), errors, failures };
  fs.writeFileSync(path.join(outDir, "playwright_qa.json"), JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2)); process.exitCode = failures.length ? 1 : 0;
}
main().catch((error) => { console.error(error.stack || String(error)); process.exitCode = 1; });