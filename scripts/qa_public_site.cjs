const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3];
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const repoRoot = path.resolve(__dirname, "..");

function number(text) {
  return Number(String(text).replace(/,/g, ""));
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const launchOptions = fs.existsSync(chromePath) ? { executablePath: chromePath, headless: true } : { headless: true };
  const browser = await chromium.launch(launchOptions);
  const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot, encoding: "utf8" }).trim();
  const sourceHashes = Object.fromEntries(["index.html", "styles.css", "app.js", "data.js", "case_studies.js"].map((name) => [
    name, crypto.createHash("sha256").update(fs.readFileSync(path.join(repoRoot, name))).digest("hex")
  ]));
  const errors = [];
  const checks = {};
  const downloads = {};
  try {
    const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const page = await desktop.newPage();
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(`console:${message.text()}`);
    });
    await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector(".result-card", { timeout: 15000 });

    checks.title = await page.title();
    checks.counts = {
      funding: await page.locator("#fundingCount").innerText(),
      resources: await page.locator("#resourceCount").innerText(),
      cases: await page.locator("#caseStudyCount").innerText(),
    };
    checks.applicantUnreachable = await page.evaluate(() => fundingResources
      .filter((item) => !matchesAny(cleanText(item.eligible_users).toLowerCase(), applicantOptions.map(([value]) => value)))
      .map((item) => item.item_id));
    checks.desktopNoOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
    checks.duplicateIds = await page.evaluate(() => {
      const ids = [...document.querySelectorAll("[id]")].map((node) => node.id);
      return ids.filter((id, index) => ids.indexOf(id) !== index);
    });
    checks.firstResultTop = await page.locator(".result-card").first().evaluate((node) => Math.round(node.getBoundingClientRect().top + window.scrollY));
    await page.locator("#resetButton").focus();
    checks.focusRule = await page.locator("#resetButton").evaluate((node) => getComputedStyle(node).outlineColor);

    await page.locator('[data-mode="Case Study"]').click();
    checks.caseMatches = number(await page.locator("#matchCount").innerText());
    checks.caseCardsOnly = await page.locator(".result-card:not(.case-study)").count() === 0;
    checks.caseLinks = await page.locator(".case-link[href^='http']").count();
    checks.caseLinkLabel = await page.locator(".case-link").first().innerText();
    checks.topicBoundaries = await page.evaluate(() => ({
      cultureDoesNotMatchAgriculture: !matchesAny("agriculture", ["culture"]),
      landDoesNotMatchMaryland: !matchesAny("maryland", ["land"]),
      artsMatch: matchesAny("cultural arts center", ["culture|arts"]),
    }));

    await page.selectOption("#stateSelect", { label: "Virginia" });
    await page.getByLabel("Parks, trails, and outdoor access").check();
    checks.virginiaTrailCases = number(await page.locator("#matchCount").innerText());
    checks.sameStateBoostVisible = await page.locator(".result-card").filter({ hasText: "Example from your selected state or territory" }).count() > 0;

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.selectOption("#placeTypeSelect", { label: "Tribal community" });
    checks.tribalCaseMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.selectOption("#stageSelect", { label: "Cleanup" });
    checks.cleanupCaseMatches = number(await page.locator("#matchCount").innerText());
    checks.cleanupCasesAreBrownfields = await page.locator(".result-card.case-study").evaluateAll((nodes) =>
      nodes.every((node) => node.textContent.includes("EPA Brownfields Success Stories"))
    );
    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.selectOption("#placeTypeSelect", "town_or_city");
    checks.townCaseMatches = number(await page.locator("#matchCount").innerText());
    checks.townCasesExact = checks.townCaseMatches === 359;

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.fill("#communityName", "St. Paul, Virginia");
    checks.namedCommunityTopTitles = (await page.locator(".result-card h4").allInnerTexts()).slice(0, 10);
    checks.namedCommunityBoostVisible = await page.locator(".result-card").filter({ hasText: "Directly references your community" }).count() > 0;
    await page.fill("#communityName", "Gallup, New Mexico");
    checks.unmatchedCommunityTopTitles = (await page.locator(".result-card h4").allInnerTexts()).slice(0, 10);
    checks.communityRankingChanges = JSON.stringify(checks.namedCommunityTopTitles) !== JSON.stringify(checks.unmatchedCommunityTopTitles);

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Funding"]').click();
    await page.selectOption("#stageSelect", { label: "Planning" });
    await page.fill("#keywordSearch", "Community Development Block Grant");
    checks.mixedFundingStageMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.getByLabel("Energy, climate, and cleanup").check();
    await page.fill("#keywordSearch", "Ralls County Electric");
    checks.electricEnergyTopicMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Funding"]').click();
    await page.getByLabel("Community services").check();
    await page.fill("#keywordSearch", "Community Facilities");
    checks.communityFacilitiesTopicMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Resource"]').click();
    checks.resourceMatches = number(await page.locator("#matchCount").innerText());
    checks.resourceCardsOnly = await page.locator(".result-card:not(.resource)").count() === 0;
    checks.resourceOfficialLinks = await page.locator(".result-card.resource .case-link[href^='http']").count();

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Funding"]').click();
    await page.getByLabel("Other or varies by program").check();
    checks.otherApplicantMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Resource"]').click();
    await page.selectOption("#stateSelect", { label: "Virginia" });
    await page.fill("#keywordSearch", "Appalachian Regional Commission Service Area");
    checks.appalachianResourceMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Funding"]').click();
    await page.getByLabel("Local government").check();
    checks.localGovernmentMatches = number(await page.locator("#matchCount").innerText());
    checks.fundingOfficialLinks = await page.locator(".result-card.funding .case-link[href^='http']").count();
    checks.applicantEligibilityFiltered = await page.locator(".result-card .details").evaluateAll((nodes) =>
      nodes.filter((_, index) => index % 2 === 0).every((node) =>
        /local governments?|municipal(?:ity|ities)?|count(?:y|ies)|cit(?:y|ies)|towns?|villages?/i.test(node.textContent)
      )
    );

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Funding"]').click();
    await page.selectOption("#stateSelect", { label: "American Samoa" });
    checks.territoryNationalCaution = await page.locator(".result-card").filter({ hasText: "confirm territory eligibility" }).count() > 0;
    await page.fill("#keywordSearch", "Office of Insular Affairs");
    checks.territoryMultiStateMatches = number(await page.locator("#matchCount").innerText());

    await page.locator("#resetButton").click();
    await page.locator('[data-mode="Case Study"]').click();
    await page.fill("#keywordSearch", "trail");
    const csvEvent = page.waitForEvent("download");
    await page.locator("#exportCsv").click();
    const csvDownload = await csvEvent;
    const csvPath = path.join(outDir, "community-export.csv");
    await csvDownload.saveAs(csvPath);
    const csvText = fs.readFileSync(csvPath, "utf8");
    downloads.csv = {
      bytes: fs.statSync(csvPath).size,
      rows: csvText.split(/\r?\n/).filter(Boolean).length - 1,
      hasLinkColumn: csvText.includes("Current Link"),
      hasOfficialUrl: /https:\/\/(www\.epa\.gov|toolkit\.climate\.gov|www\.rd\.usda\.gov)/.test(csvText),
    };

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
    const fullFiles = [
      "downloads/RERC_Community_Explorer_Appendix_2026-07-18.docx",
      "downloads/RERC_Community_Explorer_Master_2026-07-18.xlsx",
      "downloads/RERC_Community_Explorer_Master_2026-07-18.csv",
    ];
    downloads.full = {};
    for (const relative of fullFiles) {
      const response = await page.request.get(baseUrl + relative, { timeout: 60000 });
      downloads.full[path.basename(relative)] = { status: response.status(), bytes: (await response.body()).length };
    }
    if (baseUrl.includes("github.io")) {
      const pycResponse = await page.request.get(baseUrl + "rercie/__pycache__/rercie_core.cpython-312.pyc", { timeout: 60000 });
      checks.pycNotPublished = pycResponse.status() === 404;
    } else {
      checks.pycNotPublished = true;
    }

    await page.screenshot({ path: path.join(outDir, "desktop.png"), fullPage: true });
    await desktop.close();

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const mobilePage = await mobile.newPage();
    mobilePage.on("pageerror", (error) => errors.push(`mobile-pageerror:${error.message}`));
    await mobilePage.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await mobilePage.waitForSelector(".result-card", { timeout: 15000 });
    checks.mobileNoOverflow = await mobilePage.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
    checks.mobileTabsVisible = await mobilePage.locator("[data-mode]").evaluateAll((nodes) => nodes.every((node) => node.getBoundingClientRect().width >= 44));
    checks.mobileFilterCollapsed = await mobilePage.locator(".filters").evaluate((node) => getComputedStyle(node).display === "none");
    checks.mobileCollapsedControlsHidden = await mobilePage.locator(".filters input, .filters select, .filters button").evaluateAll((nodes) =>
      nodes.every((node) => node.getClientRects().length === 0)
    );
    await mobilePage.locator("#toggleFilters").click();
    checks.mobileFilterExpanded = await mobilePage.locator(".filters").evaluate((node) => getComputedStyle(node).display !== "none");
    await mobilePage.locator("#toggleFilters").click();
    await mobilePage.waitForTimeout(250);
    await mobilePage.locator('[data-mode="Case Study"]').click();
    checks.mobileCaseCards = await mobilePage.locator(".result-card.case-study").count();
    await mobilePage.screenshot({ path: path.join(outDir, "mobile.png"), fullPage: true });
    await mobile.close();

    const failures = [];
    if (checks.title !== "RERC Community Explorer") failures.push("title");
    if (checks.counts.funding !== "659" || checks.counts.resources !== "61" || checks.counts.cases !== "476") failures.push("counts");
    if (!checks.desktopNoOverflow || !checks.mobileNoOverflow) failures.push("overflow");
    if (checks.duplicateIds.length) failures.push("duplicate_ids");
    if (checks.focusRule !== "rgb(0, 61, 45)") failures.push("focus_indicator");
    if (checks.caseMatches !== 476 || !checks.caseCardsOnly || checks.caseLinks < 1 || checks.caseLinkLabel !== "Read the example") failures.push("case_studies");
    if (checks.virginiaTrailCases < 1 || !checks.sameStateBoostVisible || checks.tribalCaseMatches !== 14 || checks.townCaseMatches !== 359 || !checks.townCasesExact || !checks.namedCommunityBoostVisible || !checks.communityRankingChanges) failures.push("case_matching");
    if (checks.cleanupCaseMatches !== 113 || !checks.cleanupCasesAreBrownfields || checks.mixedFundingStageMatches < 1) failures.push("case_stage");
    if (checks.electricEnergyTopicMatches < 1 || checks.communityFacilitiesTopicMatches < 1) failures.push("topic_reachability");
    if (!checks.topicBoundaries.cultureDoesNotMatchAgriculture || !checks.topicBoundaries.landDoesNotMatchMaryland || !checks.topicBoundaries.artsMatch) failures.push("topic_boundaries");
    if (checks.resourceMatches < 1 || !checks.resourceCardsOnly || checks.resourceOfficialLinks < 1) failures.push("resources");
    if (checks.otherApplicantMatches < 1 || checks.applicantUnreachable.length) failures.push("applicant_reachability");
    if (checks.appalachianResourceMatches < 1) failures.push("broad_geography");
    if (!checks.pycNotPublished) failures.push("deployment_hygiene");
    if (checks.localGovernmentMatches < 1 || !checks.applicantEligibilityFiltered || checks.fundingOfficialLinks < 1) failures.push("eligibility");
    if (!checks.territoryNationalCaution || checks.territoryMultiStateMatches < 1) failures.push("territory_caution");
    if (downloads.csv.bytes < 100 || downloads.csv.rows < 1 || !downloads.csv.hasLinkColumn || !downloads.csv.hasOfficialUrl) failures.push("csv_export");
    if (downloads.word.bytes < 1000 || downloads.word.filename !== "RERC-community-appendix.docx" || !downloads.word.zipSignature) failures.push("word_export");
    if (Object.values(downloads.full).some((item) => item.status !== 200 || item.bytes < 100000)) failures.push("full_downloads");
    if (!checks.mobileTabsVisible || !checks.mobileFilterCollapsed || !checks.mobileCollapsedControlsHidden || !checks.mobileFilterExpanded || checks.mobileCaseCards < 1) failures.push("mobile");
    if (errors.length) failures.push("browser_errors");

    const result = { status: failures.length ? "FAIL" : "PASS", baseUrl, sourceCommit, sourceHashes, checks, downloads, errors, failures };
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
