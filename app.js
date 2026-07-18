"use strict";

const fundingResources = Array.isArray(window.RERC_CATALOG?.items) ? window.RERC_CATALOG.items : [];
const caseStudies = Array.isArray(window.RERC_CASE_STUDIES?.items) ? window.RERC_CASE_STUDIES.items : [];
const catalog = [...fundingResources, ...caseStudies];

const places = [
  "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia",
  "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine",
  "Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
  "New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
  "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia",
  "Washington","West Virginia","Wisconsin","Wyoming","American Samoa","Guam","Northern Mariana Islands","Puerto Rico",
  "U.S. Virgin Islands"
];

const territoryPlaces = new Set(["American Samoa","Guam","Northern Mariana Islands","Puerto Rico","U.S. Virgin Islands"]);

const applicantOptions = [
  ["local government|local governments|municipal|municipality|municipalities|county|counties|city|cities|town|towns|village|villages", "Local government"],
  ["tribe|tribes|tribal|native", "Tribe or Native community"],
  ["nonprofit|nonprofits|non-profit|non-profits|community organization|community organizations", "Nonprofit or community group"],
  ["state agency|state agencies|state government", "State agency"],
  ["business|businesses|entrepreneur|entrepreneurs|tourism|destination marketing", "Business or tourism group"],
  ["school|schools|college|colleges|university|universities|library|libraries|museum|museums", "School, library, or museum"],
  ["utility|utilities|authority|authorities|district|districts", "Utility or public authority"],
  ["landowner|landowners|individual|individuals|families", "Landowner or individual"]
];

const topicOptions = [
  ["trail|park|recreation|outdoor access", "Parks, trails, and outdoor access"],
  ["downtown|main street|gateway|placemaking", "Downtown and Main Street"],
  ["tourism|visitor|recreation economy", "Tourism and visitor economy"],
  ["business|entrepreneur|workforce|economic development", "Business and jobs"],
  ["transportation|street|bike|pedestrian|transit|mobility", "Transportation and safe access"],
  ["water|wastewater|stormwater|flood|coastal|resilience", "Water and resilience"],
  ["conservation|environment|environmental|habitat|forest|land|river|watershed", "Conservation and public lands"],
  ["historic|heritage|arts|culture|museum", "History, arts, and culture"],
  ["housing|community facility|community facilities|community services|public facilities|infrastructure|public safety|emergency services|education|health|food", "Community services"],
  ["energy|electric|electricity|power|grid|renewable|efficiency|climate|brownfield|cleanup", "Energy, climate, and cleanup"],
  ["planning|community development|data|mapping|capacity|technical assistance", "Planning and local capacity"]
];

const stages = ["Any step", "Planning", "Early Design", "Engineering", "Construction", "Implementation", "Operations/Maintenance", "Capacity Building", "Acquisition", "Cleanup"];

const elements = Object.fromEntries([
  "communityName","stateSelect","placeTypeSelect","keywordSearch","applicantOptions","topicOptions","stageSelect",
  "includeClosed","toggleFilters","resetButton","sortSelect","limitSelect","exportWord","exportCsv","communityTitle","communitySummary",
  "matchCount","fundingMatchCount","resourceMatchCount","caseStudyMatchCount","activeFilters","results","matchAnnouncement",
  "fundingCount","resourceCount","caseStudyCount","showFunding","showResources","showCases"
].map((id) => [id, document.getElementById(id)]));

let mode = "All";
let currentMatches = [];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function cleanText(value) {
  return String(value ?? "").trim();
}

function summaryTopic(item) {
  const topics = cleanText(item.topic_tags)
    .split(/[;,|]/)
    .map((topic) => topic.trim().toLowerCase().replace("/", " and "))
    .filter(Boolean)
    .slice(0, 2);
  return topics.length ? topics.join(" and ") : "community projects";
}

function publicSummary(item) {
  if (item.item_type === "Case Study") return cleanText(item.summary);
  const reviewed = {
    "RERC-FND-0017": "Helps eligible local governments identify, evaluate, and protect historic properties in Alaska.",
    "RERC-FND-0021": "Develops and repairs recreational trails and trail facilities for motorized and non-motorized use.",
    "RERC-FND-0024": "Offers potential funding for eligible snowmachine recreation projects in Alaska. Check the current program page for eligible work and cycle details.",
    "RERC-FND-0274": "Offers potential support for eligible projects connected to the Chesapeake Gateways Network. Check the current program page for applicant and project rules.",
    "RERC-FND-0475": "Supports projects that promote understanding of Japan.",
    "RERC-FND-0541": "Supports smaller transportation projects such as walking and biking facilities, recreational trails, safe routes to school, historic preservation, environmental work, overlooks, and safety studies.",
    "RERC-RES-0077": "Helps communities coordinate housing and services to prevent and end homelessness, rehouse people quickly, connect households with mainstream programs, and support long-term stability."
  };
  let text = reviewed[item.item_id] || cleanText(item.summary || item.why_it_matters);
  const placeholder = !text || text === "-" || text.length < 18 ||
    /^(potential rerc fit|purpose tags|varies by)/i.test(text) ||
    (/^for\s/i.test(text) && text.length < 80);
  if (placeholder) {
    const topic = summaryTopic(item);
    text = item.item_type === "Resource"
      ? `Offers information or technical help related to ${topic}. Check the provider's page for current services and access details.`
      : `Offers potential funding related to ${topic}. Check the current program page for eligible applicants, activities, and timing.`;
  }
  text = text[0].toUpperCase() + text.slice(1);
  return text.endsWith(".") || text.endsWith("!") || text.endsWith("?") ? text : text + ".";
}
function matchLabel(score) {
  if (score >= 80) return "High";
  if (score >= 65) return "Medium";
  return "Broad";
}

function corpus(item) {
  return [
    item.title, item.organization, item.geography, item.eligible_users, item.project_stage, item.topic_tags,
    item.support_type, item.summary, item.why_it_matters, item.case_place, item.case_state, item.case_place_type,
    item.case_program, item.case_partners
  ].join(" ").toLowerCase();
}

function topicCorpus(item) {
  return [item.title, item.organization, item.project_stage, item.topic_tags, item.support_type, item.summary, item.why_it_matters, item.case_program]
    .join(" ").toLowerCase();
}

function selectedValues(container) {
  return [...container.querySelectorAll("input:checked")].map((input) => input.value);
}

function matchesAny(text, groups) {
  if (!groups.length) return true;
  return groups.some((group) => group.split("|").some((term) => {
    const escaped = term.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\s+/g, "\\s+");
    return new RegExp(`(^|[^a-z0-9])${escaped}(?=$|[^a-z0-9])`, "i").test(text);
  }));
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
  if (!selectedPlace || item.item_type === "Case Study") return true;
  const geography = cleanText(item.geography);
  const territoryMultiState = territoryPlaces.has(selectedPlace) &&
    geography.toLowerCase().includes("multi-state") &&
    /(territor|insular|island area|office of insular affairs)/i.test(corpus(item));
  return isNational(geography) || appliesToPlace(geography, selectedPlace) || territoryMultiState;
}

function scoreItem(item, text, selectedPlace, selectedPlaceType, applicants, topics, selectedStage) {
  const topicText = topicCorpus(item);
  let score = item.item_type === "Case Study" ? 52 : 45;
  if (item.item_type === "Case Study") {
    if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) score += 18;
    if (selectedPlaceType && cleanText(item.case_place_type) === selectedPlaceType) score += 12;
    if (topics.length) score += Math.min(21, topics.filter((group) => matchesAny(topicText, [group])).length * 7);
    if (selectedStage !== "Any step" && cleanText(item.project_stage).toLowerCase() === selectedStage.toLowerCase()) score += 8;
    if (item.source_url) score += 5;
  } else {
    if (item.status === "Open when checked" || item.status === "Available") score += 18;
    if (item.status === "Recurring") score += 14;
    if (item.status === "Cycle closed") score -= 18;
    if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) score += 15;
    if (selectedPlace && isNational(cleanText(item.geography))) score += territoryPlaces.has(selectedPlace) ? 2 : 8;
    if (applicants.length && matchesAny(cleanText(item.eligible_users).toLowerCase(), applicants)) score += 12;
    if (topics.length) score += Math.min(18, topics.filter((group) => matchesAny(topicText, [group])).length * 7);
    if (selectedStage !== "Any step") score += cleanText(item.project_stage).toLowerCase() === "mixed" ? 4 : 10;
    if (item.summary) score += 3;
  }
  return Math.max(1, Math.min(99, score));
}

function getMatches() {
  const selectedPlace = elements.stateSelect.value;
  const selectedPlaceType = elements.placeTypeSelect.value;
  const applicants = selectedValues(elements.applicantOptions);
  const topics = selectedValues(elements.topicOptions);
  const selectedStage = elements.stageSelect.value;
  const keyword = elements.keywordSearch.value.trim().toLowerCase();

  const matches = catalog.filter((item) => {
    if (mode !== "All" && item.item_type !== mode) return false;
    if (!elements.includeClosed.checked && item.status === "Cycle closed") return false;
    if (!matchesGeography(item, selectedPlace)) return false;
    const text = corpus(item);
    if (keyword && !text.includes(keyword)) return false;
    if (item.item_type !== "Case Study" && !matchesAny(cleanText(item.eligible_users).toLowerCase(), applicants)) return false;
    if (!matchesAny(topicCorpus(item), topics)) return false;
    if (item.item_type === "Case Study" && selectedPlaceType &&
        cleanText(item.case_place_type) !== selectedPlaceType) return false;
    const stageText = cleanText(item.project_stage).toLowerCase();
    if (selectedStage !== "Any step") {
      const exactStage = matchesAny(stageText, [selectedStage.toLowerCase()]);
      const broadFundingStage = item.item_type !== "Case Study" && stageText === "mixed";
      if (!exactStage && !broadFundingStage) return false;
    }
    return true;
  }).map((item) => ({
    ...item,
    score: scoreItem(item, corpus(item), selectedPlace, selectedPlaceType, applicants, topics, selectedStage)
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

function matchReason(item) {
  const selectedPlace = elements.stateSelect.value;
  const selectedPlaceType = elements.placeTypeSelect.value;
  const topics = selectedValues(elements.topicOptions);
  if (item.item_type === "Case Study") {
    if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) return "Example from your selected state or territory";
    if (selectedPlaceType && cleanText(item.case_place_type) === selectedPlaceType) return "Similar community type";
    if (topics.length) return "Matches one or more selected priorities";
    return "Source-backed community example";
  }
  if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) return "Serves your selected area";
  if (topics.length) return "Matches one or more selected priorities";
  return "Broad match for rural community work";
}

function renderCard(item) {
  if (item.item_type === "Case Study") {
    const year = item.case_year ? ` | ${escapeHtml(item.case_year)}` : "";
    return `<article class="result-card case-study">
      <div>
        <div class="card-kicker">
          <span class="pill">Case study</span>
          <span>${escapeHtml(item.case_program)}</span>
        </div>
        <h3>${escapeHtml(item.title)}</h3>
        <p class="organization">${escapeHtml(item.case_place)}, ${escapeHtml(item.case_state)}${year}</p>
        <p class="summary">${escapeHtml(publicSummary(item))}</p>
        <p class="match-reason"><strong>Why it fits:</strong> ${escapeHtml(matchReason(item))}</p>
        <p class="details"><strong>Topics:</strong> ${escapeHtml(item.topic_tags || "Community development")}</p>
        <a class="case-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">Read the example</a>
      </div>
      <div class="score" aria-label="Match level: ${matchLabel(item.score)}"><strong>${matchLabel(item.score)}</strong><span>match level</span></div>
    </article>`;
  }
  const selectedPlace = elements.stateSelect.value;
  const nationalTerritoryListing = territoryPlaces.has(selectedPlace) && isNational(cleanText(item.geography)) && !appliesToPlace(item.geography, selectedPlace);
  const geography = nationalTerritoryListing ? item.geography + " (confirm territory eligibility)" : item.geography;
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
      <p class="match-reason"><strong>Why it fits:</strong> ${escapeHtml(matchReason(item))}</p>
      <p class="details"><strong>Where:</strong> ${escapeHtml(geography)} &nbsp; <strong>Who:</strong> ${escapeHtml(item.eligible_users || "Eligibility varies")}</p>
      <p class="details"><strong>Timing or amount:</strong> ${escapeHtml(timing)} &nbsp; <strong>Checked:</strong> ${escapeHtml(item.last_checked)}</p>
      <a class="case-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">${item.item_type === "Resource" ? "Open the resource" : "View program details"}</a>
    </div>
    <div class="score" aria-label="Match level: ${matchLabel(item.score)}"><strong>${matchLabel(item.score)}</strong><span>match level</span></div>
  </article>`;
}

function activeFilterSummary() {
  const values = [];
  if (elements.stateSelect.value) values.push(elements.stateSelect.value);
  if (elements.placeTypeSelect.value) values.push(elements.placeTypeSelect.options[elements.placeTypeSelect.selectedIndex].text);
  if (elements.keywordSearch.value.trim()) values.push(`Search: ${elements.keywordSearch.value.trim()}`);
  const applicants = selectedValues(elements.applicantOptions);
  const topics = selectedValues(elements.topicOptions);
  if (applicants.length) values.push(`${applicants.length} applicant choice${applicants.length === 1 ? "" : "s"}`);
  if (topics.length) values.push(`${topics.length} topic${topics.length === 1 ? "" : "s"}`);
  if (elements.stageSelect.value !== "Any step") values.push(elements.stageSelect.value);
  if (elements.includeClosed.checked) values.push("Closed rounds shown");
  return values.length ? values.join(" | ") : "Showing current national options. Add details to make the list more useful.";
}

function renderGroup(kind, title, description, items, total, className) {
  return `<section class="result-group ${className}" aria-label="${escapeHtml(title)}">
    <div class="result-group-heading">
      <div><p class="eyebrow">${escapeHtml(kind)}</p><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p></div>
      <strong>${total.toLocaleString()} matches</strong>
    </div>
    ${items.length ? items.map(renderCard).join("") : `<div class="empty-state"><h3>No ${escapeHtml(kind.toLowerCase())} matches</h3><p>Try fewer answers or a wider search.</p></div>`}
  </section>`;
}

function render() {
  currentMatches = getMatches();
  const limitValue = elements.limitSelect.value;
  const limit = limitValue === "all" ? Number.MAX_SAFE_INTEGER : Number(limitValue);
  const fundingResults = currentMatches.filter((item) => item.item_type === "Funding");
  const resourceResults = currentMatches.filter((item) => item.item_type === "Resource");
  const caseResults = currentMatches.filter((item) => item.item_type === "Case Study");
  let visible = currentMatches.slice(0, limit);
  if (mode === "All") {
    const each = limitValue === "all" ? Number.MAX_SAFE_INTEGER : Math.max(1, Math.floor(limit / 3));
    visible = [
      ...fundingResults.slice(0, each),
      ...resourceResults.slice(0, each),
      ...caseResults.slice(0, each)
    ];
  }
  const community = elements.communityName.value.trim();
  const place = elements.stateSelect.value;
  const label = community || place || "rural communities";
  const fundingMatches = fundingResults.length;
  const resourceMatches = resourceResults.length;
  const caseMatches = caseResults.length;
  const modeLabel = {
    "All": "Funding, resources, and examples",
    "Funding": "Funding",
    "Resource": "Resources",
    "Case Study": "Community examples"
  }[mode];

  elements.communityTitle.textContent = `${modeLabel} for ${label}`;
  elements.communitySummary.textContent = currentMatches.length
    ? "Match levels compare your answers. They do not confirm eligibility or guarantee that another community's approach will work in your place."
    : "Try fewer choices or a wider search.";
  elements.matchCount.textContent = currentMatches.length.toLocaleString();
  elements.fundingMatchCount.textContent = fundingMatches.toLocaleString();
  elements.resourceMatchCount.textContent = resourceMatches.toLocaleString();
  elements.caseStudyMatchCount.textContent = caseMatches.toLocaleString();
  elements.activeFilters.textContent = activeFilterSummary();
  elements.matchAnnouncement.textContent = `${currentMatches.length} matches shown for ${label}.`;
  if (!visible.length) {
    elements.results.innerHTML = `<div class="empty-state"><h3>No matches yet</h3><p>Clear one or more answers, or turn on closed rounds to see future options.</p></div>`;
  } else if (mode === "All") {
    const shownFunding = visible.filter((item) => item.item_type === "Funding");
    const shownResources = visible.filter((item) => item.item_type === "Resource");
    const shownCases = visible.filter((item) => item.item_type === "Case Study");
    elements.results.innerHTML = [
      renderGroup("Funding", "Ways to pay for the work", "Grants, loans, tax credits, and other funding options.", shownFunding, fundingMatches, "funding-group"),
      renderGroup("Resources", "Tools and technical help", "Guides, data, training, and hands-on support.", shownResources, resourceMatches, "resource-group"),
      renderGroup("Case studies", "Examples from other communities", "Source-backed examples to help teams compare approaches and ask better questions.", shownCases, caseMatches, "case-group")
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
  const headers = ["Item Type","Title","Organization or Program","Status","Geography","Who Can Use It","Project Step","Topics","Type of Help","Timing or Year","Summary","Current Link"];
  const lines = [headers.map(csvCell).join(",")];
  currentMatches.forEach((item) => lines.push([
    item.item_type, item.title, item.organization, item.status,
    item.item_type === "Case Study" ? `${item.case_place}, ${item.case_state}` : item.geography,
    item.eligible_users, item.project_stage, item.topic_tags, item.support_type,
    item.item_type === "Case Study" ? item.case_year : (item.deadline_or_availability || item.amount_or_cost),
    publicSummary(item), item.source_url
  ].map(csvCell).join(",")));
  downloadBlob(`\uFEFF${lines.join("\r\n")}`, "text/csv;charset=utf-8", "RERC-community-funding-resources-and-case-studies.csv");
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

function wordHyperlinkXml(text, relationshipId) {
  return '<w:hyperlink r:id="' + relationshipId + '"><w:r><w:rPr><w:color w:val="1B6A8F"/><w:u w:val="single"/></w:rPr><w:t>' +
    xmlEscape(text) + "</w:t></w:r></w:hyperlink>";
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
  const cases = currentMatches.filter((item) => item.item_type === "Case Study");
  const profile = activeFilterSummary();
  const relationships = [];
  const body = [];
  let relationshipNumber = 1;

  body.push(wordParagraphXml([wordRunXml("Appendix C: Funding, Resources, and Community Examples")], "Heading1"));
  body.push(wordParagraphXml([
    wordRunXml("Recreation Economy "),
    wordRunXml("for", { italic: true }),
    wordRunXml(" Rural Communities (RERC)")
  ]));
  body.push(wordParagraphXml([wordRunXml(community + ", " + place, { bold: true })]));
  body.push(wordParagraphXml([wordRunXml(profile)]));
  body.push(wordParagraphXml([
    wordRunXml("This explorer does not determine eligibility. ", { bold: true }),
    wordRunXml("Program rules and dates can change. Community examples show approaches, not guaranteed results. Confirm current requirements and local fit before making a decision.")
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
      if (item.item_type === "Case Study") {
        body.push(wordParagraphXml([
          wordRunXml("Community: ", { bold: true }),
          wordRunXml(`${item.case_place}, ${item.case_state}`),
          wordRunXml(" | Program: ", { bold: true }),
          wordRunXml(item.case_program)
        ]));
      } else {
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
      }
      if (item.source_url) {
        const relationshipId = "rId" + relationshipNumber++;
        relationships.push('<Relationship Id="' + relationshipId + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="' + xmlEscape(item.source_url) + '" TargetMode="External"/>');
        body.push(wordParagraphXml([
          wordRunXml(item.item_type === "Case Study" ? "Read the example: " : "Current program information: ", { bold: true }),
          wordHyperlinkXml(item.source_url, relationshipId)
        ]));
      }
    });
  };

  addSection("Funding Opportunities", funding);
  addSection("Resources", resources);
  addSection("Community Examples", cases);

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
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    relationships.join("") + "</Relationships>";
  const now = new Date().toISOString();
  const coreXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
    "<dc:title>RERC Community Funding, Resources, and Examples Appendix</dc:title><dc:creator>Recreation Economy for Rural Communities</dc:creator><cp:lastModifiedBy>RERC Community Explorer</cp:lastModifiedBy>" +
    '<dcterms:created xsi:type="dcterms:W3CDTF">' + now + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + now + "</dcterms:modified></cp:coreProperties>";
  const appXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
    "<Application>RERC Community Explorer</Application><AppVersion>1.0</AppVersion></Properties>";

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
  elements.placeTypeSelect.value = "";
  elements.keywordSearch.value = "";
  elements.stageSelect.value = "Any step";
  elements.includeClosed.checked = false;
  elements.sortSelect.value = "score";
  elements.limitSelect.value = "30";
  document.querySelectorAll(".filters input[type=checkbox]").forEach((input) => { input.checked = false; });
  mode = "All";
  document.querySelectorAll("[data-mode]").forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  render();
}

function initialize() {
  elements.fundingCount.textContent = fundingResources.filter((item) => item.item_type === "Funding").length.toLocaleString();
  elements.resourceCount.textContent = fundingResources.filter((item) => item.item_type === "Resource").length.toLocaleString();
  elements.caseStudyCount.textContent = caseStudies.length.toLocaleString();
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
  elements.showFunding.addEventListener("click", () => chooseMode("Funding"));
  elements.showResources.addEventListener("click", () => chooseMode("Resource"));
  elements.showCases.addEventListener("click", () => chooseMode("Case Study"));
  document.querySelectorAll("input, select").forEach((control) => control.addEventListener(control.type === "text" || control.type === "search" ? "input" : "change", render));
  elements.toggleFilters.addEventListener("click", () => {
    const open = document.querySelector(".filters").classList.toggle("open");
    elements.toggleFilters.setAttribute("aria-expanded", String(open));
    elements.toggleFilters.textContent = open ? "Hide filters" : "Show filters";
  });
  elements.resetButton.addEventListener("click", reset);
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.exportWord.addEventListener("click", exportWord);
  render();
}

initialize();
