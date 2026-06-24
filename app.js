const DATA = window.GRANT_EXPLORER_DATA;
const grants = DATA.grants || [];

const STATES = DATA.coverage?.statesAndTerritories || [
  "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia",
  "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine",
  "Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
  "New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
  "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia",
  "Washington","West Virginia","Wisconsin","Wyoming","American Samoa","Guam","Northern Mariana Islands","Puerto Rico",
  "U.S. Virgin Islands"
];

const ABBR = {
  AL:"Alabama", AK:"Alaska", AZ:"Arizona", AR:"Arkansas", CA:"California", CO:"Colorado", CT:"Connecticut",
  DE:"Delaware", FL:"Florida", GA:"Georgia", HI:"Hawaii", ID:"Idaho", IL:"Illinois", IN:"Indiana", IA:"Iowa",
  KS:"Kansas", KY:"Kentucky", LA:"Louisiana", ME:"Maine", MD:"Maryland", MA:"Massachusetts", MI:"Michigan",
  MN:"Minnesota", MS:"Mississippi", MO:"Missouri", MT:"Montana", NE:"Nebraska", NV:"Nevada", NH:"New Hampshire",
  NJ:"New Jersey", NM:"New Mexico", NY:"New York", NC:"North Carolina", ND:"North Dakota", OH:"Ohio", OK:"Oklahoma",
  OR:"Oregon", PA:"Pennsylvania", RI:"Rhode Island", SC:"South Carolina", SD:"South Dakota", TN:"Tennessee",
  TX:"Texas", UT:"Utah", VT:"Vermont", VA:"Virginia", WA:"Washington", WV:"West Virginia", WI:"Wisconsin", WY:"Wyoming",
  DC:"District of Columbia", AS:"American Samoa", GU:"Guam", MP:"Northern Mariana Islands", CNMI:"Northern Mariana Islands",
  PR:"Puerto Rico", VI:"U.S. Virgin Islands", USVI:"U.S. Virgin Islands"
};

const applicantOptions = [
  ["local government", "Local government"],
  ["nonprofit", "Nonprofit"],
  ["tribe", "Tribe or Native community"],
  ["state agency", "State agency"],
  ["utility", "Utility or energy partner"],
  ["business", "Business or DMO"],
  ["school", "School, library, or museum"],
  ["landowner", "Landowner"]
];

const focusOptions = [
  ["Direct Recreation Asset", "Parks, trails, and recreation assets"],
  ["Visitor Economy", "Tourism and visitor economy"],
  ["Downtown/Gateway", "Downtown, gateway, or main street"],
  ["Outdoor Access", "Outdoor access and conservation"],
  ["Heritage/Culture", "Arts, heritage, and culture"],
  ["Enabling Infrastructure", "Infrastructure that enables recreation"],
  ["brownfield", "Brownfields and reuse"],
  ["transportation", "Transportation and safe access"],
  ["water", "Water, wastewater, or stormwater"],
  ["energy", "Resilience, climate, or energy"]
];

const factorOptions = [
  ["rural", "Rural or small town"],
  ["tribal", "Tribal community"],
  ["disadvantaged", "Low-capacity or disadvantaged area"],
  ["flood", "Flooding, coastal, or resilience need"],
  ["historic", "Historic or cultural asset"],
  ["trail", "Trail, park, or water access asset"],
  ["downtown", "Downtown revitalization need"],
  ["brownfield", "Brownfield or cleanup site"]
];

const stages = ["Any","Planning","Early Design","Engineering","Construction","Implementation","Operations/Maintenance","Capacity Building","Acquisition","Cleanup","Mixed"];
const fundingTypes = ["Any","Grant","Technical Assistance","Rebate","Loan","Financing","Tax Credit"];

const els = {
  communityName: document.getElementById("communityName"),
  stateSelect: document.getElementById("stateSelect"),
  keywordSearch: document.getElementById("keywordSearch"),
  applicantOptions: document.getElementById("applicantOptions"),
  focusOptions: document.getElementById("focusOptions"),
  factorOptions: document.getElementById("factorOptions"),
  stageSelect: document.getElementById("stageSelect"),
  fundingTypeSelect: document.getElementById("fundingTypeSelect"),
  sortSelect: document.getElementById("sortSelect"),
  limitSelect: document.getElementById("limitSelect"),
  results: document.getElementById("results"),
  communityTitle: document.getElementById("communityTitle"),
  communitySummary: document.getElementById("communitySummary"),
  metricMatches: document.getElementById("metricMatches"),
  metricTopScore: document.getElementById("metricTopScore"),
  metricState: document.getElementById("metricState"),
  metricExport: document.getElementById("metricExport"),
  statGrantCount: document.getElementById("statGrantCount"),
  profileCanvas: document.getElementById("profileCanvas")
};

function init() {
  els.statGrantCount.textContent = DATA.validation.masterRows || grants.length;
  fillSelect(els.stateSelect, ["Any", ...STATES]);
  fillSelect(els.stageSelect, stages);
  fillSelect(els.fundingTypeSelect, fundingTypes);
  writeChecks(els.applicantOptions, applicantOptions, "applicant");
  writeChecks(els.focusOptions, focusOptions, "focus");
  writeChecks(els.factorOptions, factorOptions, "factor");
  bindEvents();
  update();
}

function fillSelect(select, values) {
  select.innerHTML = values.map(value => `<option value="${escapeAttr(value === "Any" ? "" : value)}">${escapeHtml(value)}</option>`).join("");
}

function writeChecks(container, options, name) {
  container.innerHTML = options.map(([value, label]) => `
    <label class="check"><input type="checkbox" name="${name}" value="${escapeAttr(value)}"> ${escapeHtml(label)}</label>
  `).join("");
}

function bindEvents() {
  document.querySelectorAll("input, select").forEach(el => el.addEventListener("input", update));
  document.querySelectorAll("input[type=checkbox], input[type=radio]").forEach(el => el.addEventListener("change", update));
  els.communityName.addEventListener("blur", detectStateFromCommunity);
  document.getElementById("resetButton").addEventListener("click", reset);
  document.getElementById("exportCsv").addEventListener("click", () => exportCsv(currentResults()));
  document.getElementById("exportWord").addEventListener("click", () => exportWord(currentResults()));
}

function detectStateFromCommunity() {
  const value = els.communityName.value.trim();
  const last = value.split(",").pop().trim();
  const upper = last.toUpperCase();
  const match = STATES.find(state => state.toLowerCase() === last.toLowerCase()) || ABBR[upper];
  if (match) {
    els.stateSelect.value = match;
    update();
  }
}

function profile() {
  return {
    community: els.communityName.value.trim(),
    state: els.stateSelect.value,
    keyword: els.keywordSearch.value.trim().toLowerCase(),
    applicants: checked("applicant"),
    focuses: checked("focus"),
    factors: checked("factor"),
    stage: els.stageSelect.value,
    fundingType: els.fundingTypeSelect.value,
    matchCapacity: document.querySelector("input[name=matchCapacity]:checked")?.value || "any",
    sort: els.sortSelect.value,
    limit: els.limitSelect.value
  };
}

function checked(name) {
  return Array.from(document.querySelectorAll(`input[name=${name}]:checked`)).map(input => input.value);
}

function currentResults() {
  const p = profile();
  const scored = grants
    .map(grant => ({ grant, ...scoreGrant(grant, p) }))
    .filter(item => item.eligible && item.score > 0);
  sortResults(scored, p.sort);
  return scored;
}

function update() {
  const p = profile();
  const results = currentResults();
  const limit = p.limit === "all" ? results.length : Number(p.limit);
  renderSummary(p, results);
  renderResults(results.slice(0, limit));
  drawProfile(p, results);
}

function scoreGrant(grant, p) {
  let score = 0;
  const reasons = [];
  const cautions = [];
  const text = grantText(grant);

  if (p.state) {
    const geoMatch = grant.state === p.state || grant.state === "National" || grant.state === "Multi-State" || !grant.state || text.includes(p.state.toLowerCase());
    if (!geoMatch) return { score: 0, eligible: false, reasons, cautions };
    if (grant.state === p.state) add(28, `State-specific resource for ${p.state}`);
    else add(14, "National, regional, or multi-state resource");
  } else {
    add(grant.state ? 4 : 8, "Select a state or territory to sharpen geography matching");
  }

  for (const applicant of p.applicants) {
    if (keywordMatch(text, applicant)) add(16, `Applicant fit: ${labelFor(applicantOptions, applicant)}`);
    else if (grant.applicants.toLowerCase().includes("see program source")) cautions.push("Check applicant details before applying");
  }

  for (const focus of p.focuses) {
    if (grant.category === focus) add(22, `Project focus fit: ${labelFor(focusOptions, focus)}`);
    else if (keywordMatch(text, focus)) add(10, `Keyword fit: ${labelFor(focusOptions, focus)}`);
  }

  for (const factor of p.factors) {
    if (keywordMatch(text, factor)) add(8, `Local factor fit: ${labelFor(factorOptions, factor)}`);
  }

  if (p.stage) {
    if (grant.stage === p.stage) add(12, `Stage fit: ${p.stage}`);
    else if (grant.stage === "Mixed") add(7, "Stage fit: mixed-use program");
  }

  if (p.fundingType) {
    if (grant.type === p.fundingType) add(12, `Funding type fit: ${p.fundingType}`);
    else return { score: 0, eligible: false, reasons, cautions };
  }

  const matchText = grant.match.toLowerCase();
  if (p.matchCapacity === "limited") {
    if (/no|none|required no|not required|see program source/.test(matchText)) add(9, "Match appears manageable");
    if (/yes|%|match/.test(matchText) && !/no|none|not required/.test(matchText)) {
      score -= 8;
      cautions.push("Match may be required");
    }
  }
  if (p.matchCapacity === "available" && /yes|%|match|varies/.test(matchText)) add(6, "Match capacity aligns");

  if (grant.status === "Active - Open") add(8, "Open now");
  if (grant.status === "Recurring") add(5, "Usually comes back");
  if (p.keyword && !grantText(grant).includes(p.keyword)) return { score: 0, eligible: false, reasons, cautions };
  if (p.keyword) add(10, "Keyword match");

  if (!p.state && !p.applicants.length && !p.focuses.length && !p.factors.length && !p.stage && !p.fundingType && !p.keyword) {
    score += grant.status === "Active - Open" ? 6 : 3;
  }

  return { score: Math.max(0, Math.round(score)), eligible: true, reasons: compact(reasons).slice(0, 5), cautions: compact(cautions).slice(0, 3) };

  function add(points, reason) {
    score += points;
    reasons.push(reason);
  }
}

function grantText(grant) {
  return Object.values(grant).join(" ").toLowerCase();
}

function keywordMatch(text, keyword) {
  const aliases = {
    "local government": ["local government", "municipal", "county", "city", "town", "locality"],
    nonprofit: ["nonprofit", "non-profit", "501(c)", "foundation"],
    tribe: ["tribe", "tribal", "native", "indian"],
    "state agency": ["state agency", "state government"],
    utility: ["utility", "energy", "electric"],
    business: ["business", "for-profit", "dmo", "tourism"],
    school: ["school", "library", "museum", "education"],
    landowner: ["landowner", "private land"],
    transportation: ["transportation", "bike", "pedestrian", "road", "transit", "sidewalk"],
    water: ["water", "wastewater", "stormwater", "river", "watershed"],
    energy: ["energy", "climate", "resilience", "efficiency", "flood"],
    brownfield: ["brownfield", "cleanup", "redevelopment"],
    rural: ["rural", "small town"],
    disadvantaged: ["disadvantaged", "low-income", "capacity", "underserved"],
    flood: ["flood", "resilience", "coastal", "hazard"],
    historic: ["historic", "heritage", "culture", "arts"],
    trail: ["trail", "park", "outdoor", "recreation"],
    downtown: ["downtown", "main street", "gateway"]
  };
  const terms = aliases[keyword] || [keyword];
  return terms.some(term => text.includes(term.toLowerCase()));
}

function sortResults(results, mode) {
  results.sort((a, b) => {
    if (mode === "state") return (a.grant.state || "zz").localeCompare(b.grant.state || "zz") || b.score - a.score;
    if (mode === "type") return a.grant.type.localeCompare(b.grant.type) || b.score - a.score;
    if (mode === "deadline") return (a.grant.deadline || "zz").localeCompare(b.grant.deadline || "zz") || b.score - a.score;
    return b.score - a.score || a.grant.program.localeCompare(b.grant.program);
  });
}

function renderSummary(p, results) {
  const name = p.community || "Selected community";
  const state = p.state || "all states and territories";
  els.communityTitle.textContent = `${name} grant matches`; 
  els.communitySummary.textContent = `${results.length} grants may fit ${state}. Change the answers on the left to narrow the list.`;
  els.metricMatches.textContent = results.length;
  els.metricTopScore.textContent = results[0]?.score || 0;
  els.metricState.textContent = p.state || "All";
  els.metricExport.textContent = results.length ? "Ready" : "Empty";
}

function renderResults(results) {
  if (!results.length) {
    els.results.innerHTML = `<div class="empty">No grants match the current profile. Widen the state/territory, funding type, or project focus filters.</div>`;
    return;
  }
  els.results.innerHTML = results.map((item, index) => grantCard(item, index + 1)).join("");
}

function grantCard(item, rank) {
  const g = item.grant;
  const reasons = item.reasons.length ? item.reasons : ["May support recreation or Main Street work"];
  const cautions = item.cautions.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  return `
    <article class="grant-card">
      <div>
        <h3>${rank}. ${escapeHtml(g.program)}</h3>
        <div class="meta">
          <span class="pill">${escapeHtml(g.type)}</span>
          <span class="pill">${escapeHtml(g.category)}</span>
          <span class="pill">${escapeHtml(g.stage)}</span>
          <span class="pill">${escapeHtml(g.state || "National")}</span>
          <span class="pill">${escapeHtml(g.status)}</span>
        </div>
        <p>${escapeHtml(trim(g.purpose, 280))}</p>
        <ul class="reason-list">${reasons.map(reason => `<li>${escapeHtml(reason)}</li>`).join("")}${cautions}</ul>
      </div>
      <div class="scorebox">
        <div class="score">${item.score}</div>
        <div><strong>${escapeHtml(g.amount || "See program source")}</strong></div>
        <div>${escapeHtml(g.match || "See program source")}</div>
        <a class="source-link" href="${escapeAttr(g.url)}" target="_blank" rel="noreferrer">Source</a>
      </div>
    </article>
  `;
}

function drawProfile(p, results) {
  const canvas = els.profileCanvas;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#f3f7f5";
  ctx.fillRect(0, 0, w, h);
  const bars = [
    ["Place", p.state ? 82 : 38, "#005ea8"],
    ["Applicant", Math.min(90, p.applicants.length * 22 + 22), "#2e6f40"],
    ["Project", Math.min(92, p.focuses.length * 18 + p.factors.length * 10 + 18), "#8a6f10"],
    ["Matches", Math.min(96, results.length / 4), "#0065a8"]
  ];
  ctx.font = "700 13px Segoe UI, Arial";
  bars.forEach((bar, index) => {
    const y = 28 + index * 38;
    ctx.fillStyle = "#20313e";
    ctx.fillText(bar[0], 18, y);
    ctx.fillStyle = "#d8e0e7";
    ctx.fillRect(120, y - 12, 260, 16);
    ctx.fillStyle = bar[2];
    ctx.fillRect(120, y - 12, Math.max(8, 260 * bar[1] / 100), 16);
    ctx.fillStyle = "#20313e";
    ctx.fillText(`${Math.round(bar[1])}`, 388, y);
  });
}

function exportCsv(results) {
  const p = profile();
  const rows = results.map((item, index) => ({
    rank: index + 1,
    score: item.score,
    community: p.community,
    state: p.state,
    program: item.grant.program,
    agency: item.grant.agency,
    status: item.grant.status,
    type: item.grant.type,
    category: item.grant.category,
    stage: item.grant.stage,
    amount: item.grant.amount,
    match: item.grant.match,
    eligible_applicants: item.grant.applicants,
    reasons: item.reasons.join("; "),
    source_url: item.grant.url
  }));
  download(csvString(rows), fileStem(p) + "-grant-recommendations.csv", "text/csv;charset=utf-8");
}

function exportWord(results) {
  const p = profile();
  const top = results.slice(0, 25);
  const rows = top.map((item, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${escapeHtml(item.grant.program)}</td>
      <td>${escapeHtml(item.grant.agency)}</td>
      <td>${item.score}</td>
      <td>${escapeHtml(item.grant.type)}</td>
      <td>${escapeHtml(item.grant.amount || "See program source")}</td>
      <td>${escapeHtml(item.reasons.join("; "))}</td>
      <td>${escapeHtml(item.grant.url)}</td>
    </tr>
  `).join("");
  const body = `
    <html><head><meta charset="utf-8">
    <style>
      body{font-family:Arial,sans-serif;color:#17202a}
      h1{font-size:24px} h2{font-size:17px;margin-top:22px}
      table{border-collapse:collapse;width:100%}
      th,td{border:1px solid #999;padding:6px;vertical-align:top;font-size:10px}
      th{background:#e7f1f8}
    </style></head><body>
      <h1>Grant Recommendation Packet</h1>
      <p><strong>Community:</strong> ${escapeHtml(p.community || "Not specified")}</p>
      <p><strong>State or territory:</strong> ${escapeHtml(p.state || "All states and territories")}</p>
      <p><strong>Profile factors:</strong> ${escapeHtml([...p.applicants, ...p.focuses, ...p.factors].join(", ") || "Basic grant search")}</p>
      <p><strong>Generated:</strong> ${new Date().toLocaleDateString()}</p>
      <h2>Grant Matches</h2>
      <table>
        <thead><tr><th>Rank</th><th>Program</th><th>Agency</th><th>Score</th><th>Type</th><th>Amount</th><th>Fit Rationale</th><th>Source</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <h2>What To Do Next</h2>
      <ol>
        <li>Open each source link.</li>
        <li>Check who can apply, the deadline, and any match rules.</li>
        <li>Pick the best matches and make a simple project scope, budget, and partner list.</li>
      </ol>
    </body></html>
  `;
  download(body, fileStem(p) + "-grant-recommendations.doc", "application/msword;charset=utf-8");
}

function csvString(rows) {
  if (!rows.length) return "";
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map(header => csvCell(row[header])).join(","));
  }
  return lines.join("\r\n");
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function download(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function reset() {
  document.querySelectorAll("input[type=checkbox]").forEach(input => input.checked = false);
  document.querySelector("input[name=matchCapacity][value=any]").checked = true;
  els.communityName.value = "";
  els.keywordSearch.value = "";
  els.stateSelect.value = "";
  els.stageSelect.value = "";
  els.fundingTypeSelect.value = "";
  els.sortSelect.value = "score";
  els.limitSelect.value = "50";
  update();
}

function labelFor(options, value) {
  return options.find(option => option[0] === value)?.[1] || value;
}

function compact(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

function trim(value, limit) {
  const text = value || "";
  return text.length > limit ? text.slice(0, limit - 3).trim() + "..." : text;
}

function fileStem(p) {
  const base = `${p.community || "community"}-${p.state || "usa"}`.toLowerCase();
  return base.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "grant-screen";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value);
}

init();
