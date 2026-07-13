"use strict";

const catalog = Array.isArray(window.RERC_CATALOG?.items) ? window.RERC_CATALOG.items : [];

const places = [
  "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia",
  "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine",
  "Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
  "New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
  "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia",
  "Washington","West Virginia","Wisconsin","Wyoming","American Samoa","Guam","Northern Mariana Islands","Puerto Rico",
  "U.S. Virgin Islands"
];

const applicantOptions = [
  ["local government|municipal|county|city|town|village", "Local government"],
  ["tribe|tribal|native", "Tribe or Native community"],
  ["nonprofit|non-profit|community organization", "Nonprofit or community group"],
  ["state agency|state government", "State agency"],
  ["business|entrepreneur|tourism|destination marketing", "Business or tourism group"],
  ["school|college|university|library|museum", "School, library, or museum"],
  ["utility|authority|district", "Utility or public authority"],
  ["landowner|individual", "Landowner or individual"]
];

const topicOptions = [
  ["trail|park|recreation|outdoor access", "Parks, trails, and outdoor access"],
  ["downtown|main street|gateway|placemaking", "Downtown and Main Street"],
  ["tourism|visitor|recreation economy", "Tourism and visitor economy"],
  ["business|entrepreneur|workforce|economic development", "Business and jobs"],
  ["transportation|street|bike|pedestrian|transit|mobility", "Transportation and safe access"],
  ["water|wastewater|stormwater|flood|coastal", "Water and resilience"],
  ["conservation|habitat|forest|land|river|watershed", "Conservation and public lands"],
  ["historic|heritage|arts|culture|museum", "History, arts, and culture"],
  ["housing|community facility|health|food", "Community services"],
  ["energy|climate|brownfield|cleanup", "Energy, climate, and cleanup"],
  ["planning|data|mapping|capacity|technical assistance", "Planning and local capacity"]
];

const stages = ["Any step", "Planning", "Early Design", "Engineering", "Construction", "Implementation", "Operations/Maintenance", "Capacity Building", "Acquisition", "Cleanup"];

const elements = Object.fromEntries([
  "communityName","stateSelect","keywordSearch","applicantOptions","topicOptions","stageSelect","includeClosed",
  "resetButton","sortSelect","limitSelect","exportWord","exportCsv","communityTitle","communitySummary","matchCount",
  "fundingMatchCount","resourceMatchCount","geographyLabel","activeFilters","results","fundingCount","resourceCount"
].map((id) => [id, document.getElementById(id)]));

let mode = "Both";
let currentMatches = [];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function cleanText(value) {
  return String(value ?? "").trim();
}

function corpus(item) {
  return [item.title, item.organization, item.geography, item.eligible_users, item.project_stage, item.topic_tags,
    item.support_type, item.summary, item.why_it_matters].join(" ").toLowerCase();
}

function selectedValues(container) {
  return [...container.querySelectorAll("input:checked")].map((input) => input.value);
}

function matchesAny(text, groups) {
  if (!groups.length) return true;
  return groups.some((group) => group.split("|").some((term) => text.includes(term)));
}

function isNational(geography) {
  const value = geography.toLowerCase();
  return ["national", "nationwide", "united states", "all states", "federal"].some((term) => value.includes(term));
}

function matchesGeography(item, selectedPlace) {
  if (!selectedPlace) return true;
  const geography = cleanText(item.geography);
  return isNational(geography) || geography.toLowerCase().includes(selectedPlace.toLowerCase());
}

function scoreItem(item, text, selectedPlace, applicants, topics, selectedStage) {
  let score = 45;
  if (item.status === "Open now" || item.status === "Available") score += 18;
  if (item.status === "Recurring") score += 14;
  if (item.status === "Cycle closed") score -= 18;
  if (selectedPlace && cleanText(item.geography).toLowerCase().includes(selectedPlace.toLowerCase())) score += 15;
  if (selectedPlace && isNational(cleanText(item.geography))) score += 8;
  if (applicants.length && matchesAny(text, applicants)) score += 12;
  if (topics.length) score += Math.min(18, topics.filter((group) => matchesAny(text, [group])).length * 7);
  if (selectedStage !== "Any step" && text.includes(selectedStage.toLowerCase())) score += 10;
  if (item.summary) score += 3;
  return Math.max(1, Math.min(99, score));
}

function getMatches() {
  const selectedPlace = elements.stateSelect.value;
  const applicants = selectedValues(elements.applicantOptions);
  const topics = selectedValues(elements.topicOptions);
  const selectedStage = elements.stageSelect.value;
  const keyword = elements.keywordSearch.value.trim().toLowerCase();

  const matches = catalog.filter((item) => {
    if (mode !== "Both" && item.item_type !== mode) return false;
    if (!elements.includeClosed.checked && item.status === "Cycle closed") return false;
    if (!matchesGeography(item, selectedPlace)) return false;
    const text = corpus(item);
    if (keyword && !text.includes(keyword)) return false;
    if (!matchesAny(text, applicants)) return false;
    if (!matchesAny(text, topics)) return false;
    return true;
  }).map((item) => ({
    ...item,
    score: scoreItem(item, corpus(item), selectedPlace, applicants, topics, selectedStage)
  }));

  const sort = elements.sortSelect.value;
  matches.sort((a, b) => {
    if (sort === "title") return a.title.localeCompare(b.title);
    if (sort === "status") return a.status.localeCompare(b.status) || b.score - a.score;
    if (sort === "type") return a.item_type.localeCompare(b.item_type) || b.score - a.score;
    return b.score - a.score || a.title.localeCompare(b.title);
  });
  return matches;
}

function renderCard(item) {
  const classes = ["result-card", item.item_type === "Resource" ? "resource" : "funding", item.status === "Cycle closed" ? "closed" : ""].join(" ");
  const timing = item.deadline_or_availability || item.amount_or_cost || "See official page";
  return `<article class="${classes}">
    <div>
      <div class="card-kicker">
        <span class="pill">${escapeHtml(item.item_type)}</span>
        <span class="pill status">${escapeHtml(item.status)}</span>
        <span>${escapeHtml(item.support_type)}</span>
      </div>
      <h3><a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3>
      <p class="organization">${escapeHtml(item.organization)}</p>
      <p class="summary">${escapeHtml(item.summary || item.why_it_matters)}</p>
      <p class="details"><strong>Where:</strong> ${escapeHtml(item.geography)} &nbsp; <strong>Who:</strong> ${escapeHtml(item.eligible_users || "See official page")}</p>
      <p class="details"><strong>Timing or amount:</strong> ${escapeHtml(timing)} &nbsp; <strong>Checked:</strong> ${escapeHtml(item.last_checked)}</p>
    </div>
    <div class="score" aria-label="Match score ${item.score} out of 99"><strong>${item.score}</strong><span>fit score</span></div>
  </article>`;
}

function activeFilterSummary() {
  const values = [];
  if (elements.stateSelect.value) values.push(elements.stateSelect.value);
  if (elements.keywordSearch.value.trim()) values.push(`Search: ${elements.keywordSearch.value.trim()}`);
  const applicants = selectedValues(elements.applicantOptions);
  const topics = selectedValues(elements.topicOptions);
  if (applicants.length) values.push(`${applicants.length} applicant choice${applicants.length === 1 ? "" : "s"}`);
  if (topics.length) values.push(`${topics.length} topic${topics.length === 1 ? "" : "s"}`);
  if (elements.stageSelect.value !== "Any step") values.push(elements.stageSelect.value);
  if (elements.includeClosed.checked) values.push("Closed rounds shown");
  return values.length ? values.join(" | ") : "Showing current national options. Add details to make the list more useful.";
}

function render() {
  currentMatches = getMatches();
  const limitValue = elements.limitSelect.value;
  const visible = limitValue === "all" ? currentMatches : currentMatches.slice(0, Number(limitValue));
  const community = elements.communityName.value.trim();
  const place = elements.stateSelect.value;
  const label = community || place || "rural communities";
  const fundingMatches = currentMatches.filter((item) => item.item_type === "Funding").length;
  const resourceMatches = currentMatches.filter((item) => item.item_type === "Resource").length;

  elements.communityTitle.textContent = `${mode === "Both" ? "Funding and resources" : mode === "Funding" ? "Funding" : "Resources"} for ${label}`;
  elements.communitySummary.textContent = currentMatches.length
    ? `Review the best matches below. Open each official page before you use a deadline or program rule.`
    : `Try fewer choices or a wider search.`;
  elements.matchCount.textContent = currentMatches.length.toLocaleString();
  elements.fundingMatchCount.textContent = fundingMatches.toLocaleString();
  elements.resourceMatchCount.textContent = resourceMatches.toLocaleString();
  elements.geographyLabel.textContent = place || "U.S.";
  elements.activeFilters.textContent = activeFilterSummary();
  elements.results.innerHTML = visible.length
    ? visible.map(renderCard).join("")
    : `<div class="empty-state"><h3>No matches yet</h3><p>Clear one or more answers, or turn on closed rounds to see future options.</p></div>`;
}

function csvCell(value) {
  const text = cleanText(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadBlob(contents, mimeType, filename) {
  const blob = new Blob([contents], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportCsv() {
  const headers = ["Item Type","Title","Organization","Status","Geography","Who Can Use It","Project Step","Topics","Type of Help","Timing or Amount","Summary","Official Page","Match Score"];
  const lines = [headers.map(csvCell).join(",")];
  currentMatches.forEach((item) => lines.push([
    item.item_type, item.title, item.organization, item.status, item.geography, item.eligible_users, item.project_stage,
    item.topic_tags, item.support_type, item.deadline_or_availability || item.amount_or_cost, item.summary, item.source_url, item.score
  ].map(csvCell).join(",")));
  downloadBlob(`\ufeff${lines.join("\r\n")}`, "text/csv;charset=utf-8", "RERC-community-funding-and-resources.csv");
}

function wordEntry(item) {
  return `<div class="entry"><h3>${escapeHtml(item.title)}</h3><p><b>${escapeHtml(item.organization)}</b> | ${escapeHtml(item.status)} | ${escapeHtml(item.support_type)}</p><p>${escapeHtml(item.summary || item.why_it_matters)}</p><p><b>Where:</b> ${escapeHtml(item.geography)} | <b>Who:</b> ${escapeHtml(item.eligible_users || "See official page")}</p><p><b>Official page:</b> <a href="${escapeHtml(item.source_url)}">${escapeHtml(item.source_url)}</a></p></div>`;
}

function exportWord() {
  const community = elements.communityName.value.trim() || "Community";
  const place = elements.stateSelect.value || "United States";
  const funding = currentMatches.filter((item) => item.item_type === "Funding");
  const resources = currentMatches.filter((item) => item.item_type === "Resource");
  const profile = activeFilterSummary();
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>RERC Appendix</title><style>
    @page{margin:.7in} body{font-family:Arial,sans-serif;color:#20312b;font-size:10pt;line-height:1.35} h1{color:#00573f;font-size:24pt} h2{color:#1b6a8f;border-bottom:2px solid #00573f;padding-bottom:5px} h3{margin:0 0 3px;color:#00573f;font-size:11pt} p{margin:3px 0}.notice{background:#fff7de;border-left:5px solid #f2c14e;padding:10px}.entry{border:1px solid #d8e0dc;border-left:4px solid #00573f;padding:9px;margin:0 0 9px;page-break-inside:avoid}a{color:#1b6a8f}
  </style></head><body><h1>Appendix C: Funding and Resources</h1><p><b>${escapeHtml(community)}, ${escapeHtml(place)}</b></p><p>${escapeHtml(profile)}</p><div class="notice"><b>RERC is free planning help. It is not a grant program.</b> Program rules and dates can change. Open the official page before you apply or use a resource.</div><h2>Funding Opportunities (${funding.length})</h2>${funding.map(wordEntry).join("")}<h2>Resources (${resources.length})</h2>${resources.map(wordEntry).join("")}</body></html>`;
  downloadBlob(`\ufeff${html}`, "application/msword", "RERC-community-appendix.doc");
}

function buildCheckList(container, options, groupName) {
  container.innerHTML = options.map(([value, label], index) => `<label><input type="checkbox" name="${groupName}" value="${escapeHtml(value)}" id="${groupName}-${index}"><span>${escapeHtml(label)}</span></label>`).join("");
}

function reset() {
  elements.communityName.value = "";
  elements.stateSelect.value = "";
  elements.keywordSearch.value = "";
  elements.stageSelect.value = "Any step";
  elements.includeClosed.checked = false;
  elements.sortSelect.value = "score";
  elements.limitSelect.value = "50";
  document.querySelectorAll(".filters input[type=checkbox]").forEach((input) => { input.checked = false; });
  mode = "Both";
  document.querySelectorAll("[data-mode]").forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  render();
}

function initialize() {
  elements.fundingCount.textContent = catalog.filter((item) => item.item_type === "Funding").length.toLocaleString();
  elements.resourceCount.textContent = catalog.filter((item) => item.item_type === "Resource").length.toLocaleString();
  elements.stateSelect.innerHTML = `<option value="">All states and territories</option>${places.map((place) => `<option>${escapeHtml(place)}</option>`).join("")}`;
  elements.stageSelect.innerHTML = stages.map((stage) => `<option>${escapeHtml(stage)}</option>`).join("");
  buildCheckList(elements.applicantOptions, applicantOptions, "applicant");
  buildCheckList(elements.topicOptions, topicOptions, "topic");
  document.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => {
    mode = button.dataset.mode;
    document.querySelectorAll("[data-mode]").forEach((candidate) => {
      const active = candidate === button;
      candidate.classList.toggle("active", active);
      candidate.setAttribute("aria-pressed", String(active));
    });
    render();
  }));
  document.querySelectorAll("input, select").forEach((control) => control.addEventListener(control.type === "text" || control.type === "search" ? "input" : "change", render));
  elements.resetButton.addEventListener("click", reset);
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.exportWord.addEventListener("click", exportWord);
  render();
}

initialize();
