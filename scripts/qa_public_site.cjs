const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const baseUrl = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3] || "browser-qa";
const liveMap = process.argv.includes("--live-map");
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const checks = {}, downloads = {}, errors = [], failures = [];
const check = (name, ok) => { if (!ok) failures.push(name); };
const hasSensitiveKey = (value) => {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(hasSensitiveKey);
  return Object.entries(value).some(([key, nested]) => /^(token|api[_-]?key|secret)$/i.test(key) || hasSensitiveKey(nested));
};
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
async function mockMapLookup(page) {
  await page.route("https://nominatim.openstreetmap.org/search**", (route) => {
    const requestUrl = new URL(route.request().url());
    const query = requestUrl.searchParams.get("q") || "";
    const state = ["Puerto Rico", "New Mexico", "Virginia"].find((name) => query.includes(name)) || "Virginia";
    const countryCode = requestUrl.searchParams.get("countrycodes") || "us";
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ lat: "36.9040", lon: "-82.3110", display_name: `Selected test community, ${state}`, address: { state, country_code: countryCode } }])
    });
  });
}
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
    const page = await context.newPage(); if (!liveMap) await mockMapLookup(page);
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => { if (message.type() === "error") { const where = message.location(); errors.push(`console:${where.url}:${where.lineNumber}:${where.columnNumber}:${message.text()}`); } });
    await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("html.rerc-planner-ready"); await page.waitForSelector("#communityName", { state: "visible" });
    checks.communityFormVisibleAtStart = await page.locator("#communityFilters").isVisible();
    checks.futureStepsLockedAtStart = await page.locator('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]').evaluateAll((nodes) => nodes.every((node) => node.disabled));
    checks.resultsHiddenAtStart = await page.locator("#matchesWorkspace").isHidden();
    checks.selectorInitial = await page.evaluate(() => ({
      stateEnabled: !document.getElementById("stateSelect").disabled,
      typeDisabled: document.getElementById("placeTypeSelect").disabled,
      placeDisabled: document.getElementById("communityName").disabled,
      coverage: window.RERCExplorer.getCommunityCoverage()
    }));
    await page.locator("[data-wizard-next]").click();
    checks.blankCommunityBlocked = await page.locator('[data-wizard-panel="1"]').isVisible() && await page.locator("#stateSelect").getAttribute("aria-invalid") === "true";
    await page.selectOption("#stateSelect", { label: "Virginia" });
    await page.locator("[data-wizard-next]").click();
    checks.partialCommunityBlocked = await page.locator('[data-wizard-panel="1"]').isVisible() && await page.locator("#placeTypeSelect").getAttribute("aria-invalid") === "true";
    await page.selectOption("#placeTypeSelect", "town_or_city");
    checks.virginiaPlaceCount = await page.locator("#communityName option").count();
    await page.selectOption("#communityName", "5169936");
    await page.waitForSelector("#communityMap .osm-map-frame", { timeout: 15000 });
    checks.selectedCommunity = await page.locator("#communityName option:checked").innerText();
    checks.profileLoaded = /loaded/i.test(await page.locator("#profileStatus").innerText());
    checks.map = await page.locator("#communityMap").evaluate((node) => ({
      iframe: node.querySelector("iframe")?.getAttribute("src") || "",
      fallback: node.querySelector(".map-fallback-link")?.getAttribute("href") || ""
    }));
    checks.futureStepsUnlocked = await page.locator('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]').evaluateAll((nodes) => nodes.every((node) => !node.disabled));
    await page.locator("[data-wizard-next]").click(); checks.phase2Visible = await page.locator('[data-wizard-panel="2"]').isVisible();
    await page.locator('#workflowSteps [data-wizard-step="3"]').click(); await page.waitForSelector(".result-card");
    checks.phase3Visible = await page.locator("#matchesWorkspace").isVisible();
    check("community_gate", checks.communityFormVisibleAtStart && checks.futureStepsLockedAtStart && checks.resultsHiddenAtStart && checks.blankCommunityBlocked && checks.partialCommunityBlocked && checks.futureStepsUnlocked && checks.phase2Visible && checks.phase3Visible);
    check("community_selector", checks.selectorInitial.stateEnabled && checks.selectorInitial.typeDisabled && checks.selectorInitial.placeDisabled && checks.selectorInitial.coverage.profiles === 35902 && checks.selectorInitial.coverage.statesAndTerritories === 56 && checks.selectorInitial.coverage.countiesAndEquivalents === 3293 && checks.selectorInitial.coverage.townsCitiesAndPlaces === 32609 && checks.virginiaPlaceCount > 500 && /St\. Paul/.test(checks.selectedCommunity) && checks.profileLoaded);
    check("community_map", /openstreetmap\.org\/export\/embed\.html/.test(checks.map.iframe) && /marker=/.test(checks.map.iframe));
    checks.counts = await page.evaluate(() => ["fundingCount", "resourceCount", "caseStudyCount"].map((id) => Number(document.getElementById(id).textContent)));
    check("counts", checks.counts.join(",") === "659,137,476" && checks.counts.reduce((sum, value) => sum + value, 0) === 1272);
    checks.nextDeadline = await page.locator("#nextDeadlinePanel").evaluate((node) => ({
      visible: node.getBoundingClientRect().height > 0,
      date: node.querySelector("#nextDeadlineDate")?.textContent.trim() || "",
      program: node.querySelector("#nextDeadlineMeta")?.textContent.trim() || "",
      link: node.querySelector("#nextDeadlineLink")?.getAttribute("href") || ""
    }));
    check("next_deadline", checks.nextDeadline.visible && /\b20\d{2}\b/.test(checks.nextDeadline.date) && checks.nextDeadline.program.length > 5 && /^https:\/\//.test(checks.nextDeadline.link));
    checks.deadlineParser = await page.evaluate(() => {
      const iso = (value) => value ? `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}` : "";
      const now = new Date();
      const todayText = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
      return {
        expectedToday: todayText,
        openThenDue: iso(parseDeadline({ status: "Open", deadline_or_availability: "Cycle opens July 27, 2026; proposals due August 14, 2026" })),
        dateRange: iso(parseDeadline({ status: "Open", deadline_or_availability: "Application period 2026-08-14 to 2026-10-31" })),
        recurringList: iso(parseDeadline({ status: "Open", deadline_or_availability: "2026 deadlines include July 1, September 1, November 2" })),
        shorthandRange: iso(parseDeadline({ status: "Upcoming", deadline_or_availability: "Application period April 2-4, 2099" })),
        dueToday: iso(parseDeadline({ status: "Open", deadline_or_availability: `Applications due ${todayText}` })),
        dueTodayHour: parseDeadline({ status: "Open", deadline_or_availability: `Applications due ${todayText}` })?.getHours()
      };
    });
    check("deadline_parser", checks.deadlineParser.openThenDue === "2026-08-14" && checks.deadlineParser.dateRange === "2026-10-31" && checks.deadlineParser.recurringList === "2026-09-01" && checks.deadlineParser.shorthandRange === "2099-04-04" && checks.deadlineParser.dueToday === checks.deadlineParser.expectedToday && checks.deadlineParser.dueTodayHour === 0);
    checks.eagle = await page.locator(".rercie-mascot").evaluate((image) => {
      const style = getComputedStyle(image), box = image.getBoundingClientRect();
      return { loaded: image.complete && image.naturalWidth > 0, objectFit: style.objectFit, objectPosition: style.objectPosition, ratio: box.width / box.height };
    });
    check("eagle_centered", checks.eagle.loaded && checks.eagle.objectFit === "contain" && /50%|center/.test(checks.eagle.objectPosition) && Math.abs(checks.eagle.ratio - (16 / 9)) < 0.03);
    checks.desktopNoOverflow = await overflow(page); check("desktop_overflow", checks.desktopNoOverflow);
    const modes = { modeAll: '[data-mode="All"]', modeFunding: "#showFunding", modeResources: "#showResources", modeCases: "#showCases" };
    checks.modes = {}; for (const [name, selector] of Object.entries(modes)) { await page.locator(selector).click(); checks.modes[name] = await page.locator(selector).getAttribute("aria-pressed") === "true"; }
    check("mode_buttons", Object.values(checks.modes).every(Boolean));
    await page.locator("#showFunding").click();
    checks.cardActions = await page.locator(".result-card").first().evaluate((card) => ({
      planner: card.querySelectorAll(".planner-card-actions [data-action]").length,
      duplicateBase: card.querySelectorAll(".card-actions [data-action]").length
    }));
    check("single_card_actions", checks.cardActions.planner === 2 && checks.cardActions.duplicateBase === 0);
    await page.locator("#showFundingCalendar").click();
    await page.locator("#fundingCalendar").waitFor({ state: "visible" });
    const monthBefore = await page.locator("#calendarMonthTitle").innerText();
    await page.locator("#nextCalendarMonth").click();
    const monthAfter = await page.locator("#calendarMonthTitle").innerText();
    checks.calendar = {
      visible: await page.locator("#fundingCalendar").isVisible(),
      weekdayHeaders: await page.locator("#calendarGrid .calendar-weekday").count(),
      dayCells: await page.locator("#calendarGrid .calendar-day").count(),
      agendaItems: await page.locator("#calendarAgenda .calendar-agenda-item").count(),
      navigated: monthBefore !== monthAfter,
      cardsHidden: await page.locator("#results").isHidden()
    };
    check("funding_calendar", checks.calendar.visible && checks.calendar.weekdayHeaders === 7 && checks.calendar.dayCells >= 28 && checks.calendar.agendaItems > 0 && checks.calendar.navigated && checks.calendar.cardsHidden);
    await page.screenshot({ path: path.join(outDir, "calendar-desktop.png"), fullPage: true });
    await page.locator("#showFundingList").click();
    const datedTitle = await page.evaluate(() => window.RERCExplorer.getMatches().find((item) => { const date = item.item_type === "Funding" ? window.RERCExplorer.parseDeadline(item) : null; return date instanceof Date && !Number.isNaN(date.getTime()) && date.getTime() >= new Date().setHours(0, 0, 0, 0); })?.title || "");
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
    checks.spanishApplied = await page.locator("html").getAttribute("lang") === "es"
      && /Espa/.test(await page.locator("#openLanguage span").innerText())
      && /Recursos/.test(await page.locator("#showResources").innerText())
      && /Descargar RERC-e/.test(await page.locator("#rercieDownload").innerText())
      && /Descargue todo el cat[aá]logo/.test(await page.locator("#downloadsTitle").innerText())
      && /Primero, cu[eé]ntenos/.test(await page.locator("#communityFilters").innerText())
      && /Guardar|Quitar/.test(await page.locator('[data-action="planner-save"]').first().innerText())
      && await page.evaluate(() => document.activeElement?.id === "openLanguage"); check("spanish_applied", checks.spanishApplied);
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
      const mobile = await browser.newContext({ viewport: { width, height: 844 } }); const page = await mobile.newPage(); if (!liveMap) await mockMapLookup(page); page.on("pageerror", (error) => errors.push(`mobile:${error.message}`));
      await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 }); await page.waitForSelector("html.rerc-planner-ready"); await page.waitForSelector("#communityName", { state: "visible" });
      const formVisible = await page.locator("#communityFilters").isVisible();
      const locked = await page.locator('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]').evaluateAll((nodes) => nodes.every((node) => node.disabled));
      await page.selectOption("#stateSelect", { label: "New Mexico" }); await page.selectOption("#placeTypeSelect", "town_or_city"); await page.selectOption("#communityName", "3576200"); await page.waitForSelector("#communityMap .osm-map-frame", { timeout: 15000 });
      await page.locator('#workflowSteps [data-wizard-step="2"]').click(); const phase2 = await page.locator('[data-wizard-panel="2"]').isVisible();
      await page.locator('#workflowSteps [data-wizard-step="3"]').click(); await page.waitForSelector(".result-card");
      const controls = await page.locator("button, a, input, select").evaluateAll((nodes) => nodes.filter((node) => { const style = getComputedStyle(node), box = node.getBoundingClientRect(); return !node.matches('input[type="file"]') && style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0; }).map((node) => Math.min(node.getBoundingClientRect().width, node.getBoundingClientRect().height)));
      await page.locator('[data-mobile-action="filters"]').click(); const communityAction = await page.locator("#communityFilters").isVisible() && await page.locator('[data-wizard-panel="1"]').isVisible();
      checks.mobile[width] = { overflow: await overflow(page), bottomNav: await page.locator(".mobile-nav").isVisible(), controls44: controls.every((value) => value >= 44), formVisible, locked, phase2, communityAction }; check(`mobile_${width}`, Object.values(checks.mobile[width]).every(Boolean));
      await page.screenshot({ path: path.join(outDir, `mobile-${width}.png`), fullPage: true }); await mobile.close();
    }
    const territoryContext = await browser.newContext({ viewport: { width: 1024, height: 800 } });
    const territoryPage = await territoryContext.newPage();
    if (!liveMap) await mockMapLookup(territoryPage);
    territoryPage.on("pageerror", (error) => errors.push(`territory:${error.message}`));
    await territoryPage.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
    await territoryPage.waitForSelector("html.rerc-planner-ready");
    await territoryPage.selectOption("#stateSelect", { label: "Puerto Rico" });
    await territoryPage.selectOption("#placeTypeSelect", "county_or_region");
    await territoryPage.selectOption("#communityName", "72049");
    await territoryPage.waitForSelector("#communityMap .osm-map-frame", { timeout: 15000 });
    checks.territoryMap = await territoryPage.evaluate(() => ({
      state: document.getElementById("stateSelect").value,
      place: document.getElementById("communityName").selectedOptions[0]?.textContent || "",
      frame: document.querySelector("#communityMap iframe")?.getAttribute("src") || "",
      profileState: window.RERCExplorer.getSelectedCommunityProfile()?.state || ""
    }));
    check("territory_map", checks.territoryMap.state === "Puerto Rico" && /Culebra/.test(checks.territoryMap.place) && checks.territoryMap.profileState === "Puerto Rico" && /marker=/.test(checks.territoryMap.frame));
    await territoryContext.close();
    check("browser_errors", errors.length === 0);
  } finally { await browser.close(); }
  const report = { status: failures.length ? "FAIL" : "PASS", baseUrl, checks, downloads: Object.fromEntries(Object.entries(downloads).map(([name, item]) => [name, { name: item.name, bytes: item.bytes }])), errors, failures };
  fs.writeFileSync(path.join(outDir, "playwright_qa.json"), JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2)); process.exitCode = failures.length ? 1 : 0;
}
main().catch((error) => { console.error(error.stack || String(error)); process.exitCode = 1; });
