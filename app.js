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
  "fundingMatchCount","resourceMatchCount","geographyLabel","activeFilters","results","fundingCount","resourceCount","showResources"
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

function publicSummary(item) {
  const reviewed = {
    "RERC-FND-0021": "Develops and repairs recreational trails and trail facilities for motorized and non-motorized use.",
    "RERC-FND-0475": "Supports projects that promote understanding of Japan.",
    "RERC-FND-0541": "Supports smaller transportation projects such as walking and biking facilities, recreational trails, safe routes to school, historic preservation, environmental work, overlooks, and safety studies.",
    "RERC-RES-0077": "Helps communities coordinate housing and services to prevent and end homelessness, rehouse people quickly, connect households with mainstream programs, and support long-term stability."
  };
  const text = reviewed[item.item_id] || cleanText(item.summary || item.why_it_matters);
  return text.replace(/^[a-z]/, (letter) => letter.toUpperCase());
}

function matchLabel(score) {
  if (score >= 80) return "High";
  if (score >= 65) return "Medium";
  return "Broad";
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

function appliesToPlace(geography, selectedPlace) {
  const selected = cleanText(selectedPlace).toLowerCase();
  return cleanText(geography).split(/[;,|/]/).some((area) => {
    const normalized = area.trim().toLowerCase();
    return normalized === selected || normalized.startsWith(`${selected} (`);
  });
}

function matchesGeography(item, selectedPlace) {
  if (!selectedPlace) return true;
  const geography = cleanText(item.geography);
  return isNational(geography) || appliesToPlace(geography, selectedPlace);
}

function scoreItem(item, text, selectedPlace, applicants, topics, selectedStage) {
  let score = 45;
  if (item.status === "Open when checked" || item.status === "Available") score += 18;
  if (item.status === "Recurring") score += 14;
  if (item.status === "Cycle closed") score -= 18;
  if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) score += 15;
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
  const timing = item.deadline_or_availability || item.amount_or_cost || "Check current availability";
  return `<article class="${classes}">
    <div>
      <div class="card-kicker">
        <span class="pill">${escapeHtml(item.item_type)}</span>
        <span class="pill status">${escapeHtml(item.status)}</span>
        <span>${escapeHtml(item.support_type)}</span>
      </div>
      <h3>${escapeHtml(item.title)}</h3>
      <p class="organization">${escapeHtml(item.organization)}</p>
      <p class="summary">${escapeHtml(publicSummary(item))}</p>
      <p class="details"><strong>Where:</strong> ${escapeHtml(item.geography)} &nbsp; <strong>Who:</strong> ${escapeHtml(item.eligible_users || "Eligibility varies")}</p>
      <p class="details"><strong>Timing or amount:</strong> ${escapeHtml(timing)} &nbsp; <strong>Checked:</strong> ${escapeHtml(item.last_checked)}</p>
    </div>
    <div class="score" aria-label="Match level: ${matchLabel(item.score)}"><strong>${matchLabel(item.score)}</strong><span>match level</span></div>
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
  const limit = limitValue === "all" ? Number.MAX_SAFE_INTEGER : Number(limitValue);
  const fundingResults = currentMatches.filter((item) => item.item_type === "Funding");
  const resourceResults = currentMatches.filter((item) => item.item_type === "Resource");
  let visible = currentMatches.slice(0, limit);
  if (mode === "Both") {
    let fundingSlots = limitValue === "all" ? fundingResults.length : Math.ceil(limit / 2);
    let resourceSlots = limitValue === "all" ? resourceResults.length : Math.floor(limit / 2);
    if (fundingResults.length < fundingSlots) resourceSlots += fundingSlots - fundingResults.length;
    if (resourceResults.length < resourceSlots) fundingSlots += resourceSlots - resourceResults.length;
    visible = [...fundingResults.slice(0, fundingSlots), ...resourceResults.slice(0, resourceSlots)];
  }
  const community = elements.communityName.value.trim();
  const place = elements.stateSelect.value;
  const label = community || place || "rural communities";
  const fundingMatches = currentMatches.filter((item) => item.item_type === "Funding").length;
  const resourceMatches = currentMatches.filter((item) => item.item_type === "Resource").length;

  elements.communityTitle.textContent = `${mode === "Both" ? "Funding and resources" : mode === "Funding" ? "Funding" : "Resources"} for ${label}`;
  elements.communitySummary.textContent = currentMatches.length
    ? `Review the most relevant matches below. Match levels compare your answers; they do not confirm eligibility. Check current requirements with the program before you apply or make a decision.`
    : `Try fewer choices or a wider search.`;
  elements.matchCount.textContent = currentMatches.length.toLocaleString();
  elements.fundingMatchCount.textContent = fundingMatches.toLocaleString();
  elements.resourceMatchCount.textContent = resourceMatches.toLocaleString();
  elements.geographyLabel.textContent = place || "U.S.";
  elements.activeFilters.textContent = activeFilterSummary();
  if (!visible.length) {
    elements.results.innerHTML = `<div class="empty-state"><h3>No matches yet</h3><p>Clear one or more answers, or turn on closed rounds to see future options.</p></div>`;
  } else if (mode === "Both") {
    const visibleFunding = visible.filter((item) => item.item_type === "Funding");
    const visibleResources = visible.filter((item) => item.item_type === "Resource");
    elements.results.innerHTML = [
      `<section class="result-group funding-group" aria-labelledby="fundingResultsTitle"><div class="result-group-heading"><div><p class="eyebrow">Funding</p><h3 id="fundingResultsTitle">Funding opportunities</h3><p>Grants, loans, tax credits, and other ways to pay for community projects.</p></div><strong>${fundingMatches.toLocaleString()} matches</strong></div>${visibleFunding.length ? visibleFunding.map(renderCard).join("") : `<div class="empty-state"><h3>No funding matches</h3><p>Try fewer answers or a wider search.</p></div>`}</section>`,
      `<section class="result-group resource-group" aria-labelledby="resourceResultsTitle"><div class="result-group-heading"><div><p class="eyebrow">Resources</p><h3 id="resourceResultsTitle">Tools and technical help</h3><p>Guides, data, training, and hands-on help to plan and carry out the work.</p></div><strong>${resourceMatches.toLocaleString()} matches</strong></div>${visibleResources.length ? visibleResources.map(renderCard).join("") : `<div class="empty-state"><h3>No resource matches</h3><p>Try fewer answers or a wider search.</p></div>`}</section>`
    ].join("");
  } else {
    elements.results.innerHTML = visible.map(renderCard).join("");
  }
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
  const headers = ["Item Type","Title","Organization","Status","Geography","Who Can Use It","Project Step","Topics","Type of Help","Timing or Amount","Summary"];
  const lines = [headers.map(csvCell).join(",")];
  currentMatches.forEach((item) => lines.push([
    item.item_type, item.title, item.organization, item.status, item.geography, item.eligible_users, item.project_stage,
    item.topic_tags, item.support_type, item.deadline_or_availability || item.amount_or_cost, publicSummary(item)
  ].map(csvCell).join(",")));
  downloadBlob(`\ufeff${lines.join("\r\n")}`, "text/csv;charset=utf-8", "RERC-community-funding-and-resources.csv");
}

function xmlEscape(value) {
  return cleanText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function wordRunXml(text, options = {}) {
  const properties = [];
  if (options.bold) properties.push("<w:b/>");
  if (options.italic) properties.push("<w:i/>");
  if (options.color) properties.push('<w:color w:val="' + options.color + '"/>');
  return "<w:r>" + (properties.length ? "<w:rPr>" + properties.join("") + "</w:rPr>" : "") +
    '<w:t xml:space="preserve">' + xmlEscape(text) + "</w:t></w:r>";
}

function wordParagraphXml(runs, style = "") {
  const properties = style ? '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>' : "";
  return "<w:p>" + properties + runs.join("") + "</w:p>";
}

async function exportWord() {
  if (typeof JSZip === "undefined") {
    window.alert("The Word export tool did not load. Refresh the page and try again.");
    return;
  }
  const community = elements.communityName.value.trim() || "Community";
  const place = elements.stateSelect.value || "United States";
  const funding = currentMatches.filter((item) => item.item_type === "Funding");
  const resources = currentMatches.filter((item) => item.item_type === "Resource");
  const profile = activeFilterSummary();
  const relationships = [];
  const body = [];
  let relationshipNumber = 1;

  body.push(wordParagraphXml([wordRunXml("Appendix C: Funding and Resources")], "Heading1"));
  body.push(wordParagraphXml([
    wordRunXml("Recreation Economy "),
    wordRunXml("for", { italic: true }),
    wordRunXml(" Rural Communities (RERC)")
  ]));
  body.push(wordParagraphXml([wordRunXml(community + ", " + place, { bold: true })]));
  body.push(wordParagraphXml([wordRunXml(profile)]));
  body.push(wordParagraphXml([
    wordRunXml("RERC is free planning help. It is not a grant program. ", { bold: true }),
    wordRunXml("Program rules and dates can change. Check current requirements with the program before you apply or use a resource.")
  ], "Notice"));

  const addSection = (title, items) => {
    body.push(wordParagraphXml([wordRunXml(title + " (" + items.length + ")")], "Heading2"));
    items.forEach((item) => {
      body.push(wordParagraphXml([wordRunXml(item.title)], "Heading3"));
      body.push(wordParagraphXml([
        wordRunXml(item.organization, { bold: true }),
        wordRunXml(" | " + item.status + " | " + item.support_type)
      ]));
      body.push(wordParagraphXml([wordRunXml(publicSummary(item))]));
      body.push(wordParagraphXml([
        wordRunXml("Where: ", { bold: true }),
        wordRunXml(item.geography),
        wordRunXml(" | Who: ", { bold: true }),
        wordRunXml(item.eligible_users || "Eligibility varies")
      ]));
      body.push(wordParagraphXml([
        wordRunXml("Last checked: ", { bold: true }),
        wordRunXml(item.last_checked || "Not recorded")
      ]));
    });
  };

  addSection("Funding Opportunities", funding);
  addSection("Resources", resources);

  const documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
    "<w:body>" + body.join("") +
    '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1008" w:right="1008" w:bottom="1008" w:left="1008" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>' +
    "</w:body></w:document>";
  const stylesXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="42"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="1B6A8F"/><w:sz w:val="30"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="160" w:after="40"/><w:keepNext/></w:pPr><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="23"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Notice"><w:name w:val="Notice"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="100" w:after="180"/><w:shd w:fill="FFF7DE"/><w:ind w:left="160" w:right="160"/></w:pPr></w:style>' +
    "</w:styles>";
  const contentTypes = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
    "</Types>";
  const rootRelationships = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>' +
    "</Relationships>";
  const documentRelationships = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>';
  const now = new Date().toISOString();
  const coreXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
    "<dc:title>RERC Community Funding and Resources Appendix</dc:title><dc:creator>Recreation Economy for Rural Communities</dc:creator><cp:lastModifiedBy>RERC Funding and Resource Finder</cp:lastModifiedBy>" +
    '<dcterms:created xsi:type="dcterms:W3CDTF">' + now + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + now + "</dcterms:modified></cp:coreProperties>";
  const appXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
    "<Application>RERC Funding and Resource Finder</Application><AppVersion>1.0</AppVersion></Properties>";

  const zip = new JSZip();
  zip.file("[Content_Types].xml", contentTypes);
  zip.file("_rels/.rels", rootRelationships);
  zip.file("docProps/core.xml", coreXml);
  zip.file("docProps/app.xml", appXml);
  zip.file("word/document.xml", documentXml);
  zip.file("word/styles.xml", stylesXml);
  zip.file("word/_rels/document.xml.rels", documentRelationships);
  const docx = await zip.generateAsync({ type: "uint8array", compression: "DEFLATE" });
  downloadBlob(docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "RERC-community-appendix.docx");
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
  elements.stateSelect.innerHTML = `<option value="">All states, D.C., and U.S. territories</option>${places.map((place) => `<option>${escapeHtml(place)}</option>`).join("")}`;
  elements.stageSelect.innerHTML = stages.map((stage) => `<option>${escapeHtml(stage)}</option>`).join("");
  buildCheckList(elements.applicantOptions, applicantOptions, "applicant");
  buildCheckList(elements.topicOptions, topicOptions, "topic");
  function chooseMode(nextMode) {
    mode = nextMode;
    document.querySelectorAll("[data-mode]").forEach((candidate) => {
      const active = candidate.dataset.mode === mode;
      candidate.classList.toggle("active", active);
      candidate.setAttribute("aria-pressed", String(active));
    });
    render();
  }
  document.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => chooseMode(button.dataset.mode)));
  elements.showResources.addEventListener("click", () => chooseMode("Resource"));
  document.querySelectorAll("input, select").forEach((control) => control.addEventListener(control.type === "text" || control.type === "search" ? "input" : "change", render));
  elements.resetButton.addEventListener("click", reset);
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.exportWord.addEventListener("click", exportWord);
  render();
}

initialize();
