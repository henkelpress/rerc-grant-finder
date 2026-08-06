const { chromium } = require("playwright");
const fs = require("fs");
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

(async function () {
  const browser = await chromium.launch(fs.existsSync(chromePath)
    ? { executablePath: chromePath, headless: true }
    : { headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(process.argv[2] || "http://127.0.0.1:4175/", { waitUntil: "networkidle" });
    await page.waitForSelector("html.rerc-planner-ready");
    await page.locator("#stateSelect").selectOption({ label: "Virginia" });
    await page.locator('[data-wizard-step="3"]').click();
    await page.locator('[data-action="planner-save"]').first().click();
    await page.waitForTimeout(300);

    const currentPhase = await page.locator("#roadmap select").first().inputValue();
    const nextPhase = currentPhase === "Build" ? "Plan" : "Build";
    await page.locator("#roadmap select").first().selectOption(nextPhase);
    await page.waitForTimeout(300);
    const before = await page.evaluate(function () {
      return {
        id: localStorage.getItem("rerc.activeWorkspaceId.v2"),
        phase: document.querySelector("#roadmap select")?.value,
        status: document.querySelector("#plannerStatus")?.textContent,
      };
    });

    page.once("dialog", function (dialog) { dialog.accept(); });
    await page.locator("#deleteLocalData").click();
    await page.waitForTimeout(300);
    const after = await page.evaluate(function () {
      return {
        id: localStorage.getItem("rerc.activeWorkspaceId.v2"),
        count: Number(document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0),
        button: document.querySelector("#deleteLocalData")?.textContent,
      };
    });

    const passed = /^browser-/.test(before.id || "") && before.phase === nextPhase &&
      new RegExp(`Moved to ${nextPhase}`).test(before.status || "") && /^browser-/.test(after.id || "") &&
      after.id !== before.id && after.count === 0 && /Reset roadmap/.test(after.button || "");
    console.log(JSON.stringify({ status: passed ? "PASS" : "FAIL", before, after }, null, 2));
    process.exitCode = passed ? 0 : 1;
  } finally {
    await browser.close();
  }
})().catch(function (error) {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
