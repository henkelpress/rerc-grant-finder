(function (root, factory) {
  "use strict";

  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.RERCDeadlineUtils = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function cleanText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

function makeLocalDate(year, month, day) {
  const date = new Date(year, month - 1, day, 0, 0, 0, 0);
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : null;
}

function parseDeadline(item) {
  const text = cleanText(item?.deadline_or_availability);
  if (!text || /\b(rolling|ongoing|check|anticipated|expected|forthcoming|to be announced|tba|varies|not announced|pending|when available|until funds? (?:are )?depleted|open until filled|continuous)\b/i.test(text)) {
    return null;
  }

  const candidates = [];
  const addCandidate = (year, month, day, index, length) => {
    const date = makeLocalDate(Number(year), Number(month), Number(day));
    if (date) candidates.push({ date, index, end: index + length, rangeStart: false, rangeEnd: false });
  };

  for (const match of text.matchAll(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/g)) {
    addCandidate(match[1], match[2], match[3], match.index, match[0].length);
  }
  for (const match of text.matchAll(/\b(\d{1,2})\/(\d{1,2})\/(20\d{2})\b/g)) {
    addCandidate(match[3], match[1], match[2], match.index, match[0].length);
  }

  const monthNumbers = {
    january: 1, jan: 1, february: 2, feb: 2, march: 3, mar: 3, april: 4, apr: 4,
    may: 5, june: 6, jun: 6, july: 7, jul: 7, august: 8, aug: 8, september: 9,
    sep: 9, sept: 9, october: 10, oct: 10, november: 11, nov: 11, december: 12, dec: 12
  };
  const monthPattern = Object.keys(monthNumbers).join("|");
  const shorthandRangePattern = new RegExp(`\\b(${monthPattern})\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?\\s*(?:-|\\u2013|\\u2014|to|through)\\s*(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(20\\d{2})\\b`, "gi");
  for (const match of text.matchAll(shorthandRangePattern)) {
    const month = monthNumbers[match[1].toLowerCase()];
    const startDate = makeLocalDate(Number(match[4]), month, Number(match[2]));
    const endDate = makeLocalDate(Number(match[4]), month, Number(match[3]));
    if (!startDate || !endDate || endDate < startDate) continue;
    const endOffset = match[0].lastIndexOf(match[3]);
    candidates.push({ date: startDate, index: match.index, end: match.index + match[0].indexOf(match[3]), rangeStart: true, rangeEnd: false });
    candidates.push({ date: endDate, index: match.index + endOffset, end: match.index + endOffset + match[3].length, rangeStart: false, rangeEnd: true });
  }
  const listYear = text.match(/\b(20\d{2})\s+(?:deadlines?|cycle|application period)\b/i)?.[1];
  const namedDatePattern = new RegExp(`\\b(${monthPattern})\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?(?:,?\\s+(20\\d{2}))?\\b`, "gi");
  for (const match of text.matchAll(namedDatePattern)) {
    const year = match[3] || listYear;
    if (year) addCandidate(year, monthNumbers[match[1].toLowerCase()], match[2], match.index, match[0].length);
  }
  if (!candidates.length) return null;
  candidates.sort((a, b) => a.index - b.index);
  for (let index = 0; index < candidates.length - 1; index += 1) {
    const between = text.slice(candidates[index].end, candidates[index + 1].index);
    if (/^\s*(?:to|through|-)\s*$/i.test(between)) {
      candidates[index].rangeStart = true;
      candidates[index + 1].rangeEnd = true;
    }
  }

  const isOpeningDate = (entry) => {
    const prefix = text.slice(Math.max(0, entry.index - 40), entry.index);
    return entry.rangeStart || (!entry.rangeEnd && /\b(open(?:s|ing)?|begins?|starts?|from)\b[^.;:]{0,24}$/i.test(prefix));
  };
  const usable = candidates.filter((entry) => !isOpeningDate(entry));
  if (!usable.length) return null;
  const deadlineList = /\bdeadlines?\s+(?:include|are)\b/i.test(text);
  const anchored = usable.filter((entry) => {
    const context = text.slice(Math.max(0, entry.index - 50), Math.min(text.length, entry.end + 24));
    return deadlineList || entry.rangeEnd || /\b(due|deadline|closes?|closing|ends?|through)\b/i.test(context);
  });
  const pool = anchored.length ? anchored : usable;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const future = pool.filter((entry) => entry.date >= today).sort((a, b) => a.date - b.date);
  if (future.length) return future[0].date;
  const deadline = pool.sort((a, b) => b.date - a.date)[0].date;
  if (/\b(open|available)\b/i.test(cleanText(item.status)) && deadline < today) return null;
  return deadline;
}
function fundingTiming(item) {
  const raw = cleanText(item?.deadline_or_availability);
  const status = cleanText(item?.status);
  const date = parseDeadline(item);
  if (date) return { type: "dated", label: "Dated deadline", detail: raw, date };
  if (/\b(rolling|ongoing|year[- ]round|continuous|always open|open throughout the year|no fixed deadlines?|first[- ]come,? first[- ]served|as needed|while (?:funding|funds) remain|until funds? (?:are )?depleted|applications? (?:are )?accepted (?:throughout|year[- ]round))\b/i.test(raw)) {
    return { type: "rolling", label: "Rolling / ongoing", detail: raw, date: null };
  }
  if (/\b(cycle closed|round closed|has ended|ended|awarded|wrapped|not accepting|no current round|next round|future round|deadline passed)\b/i.test(`${status} ${raw}`)) {
    return { type: "closed", label: "Closed / next cycle pending", detail: raw, date: null };
  }
  if (/\b(deadlines? vary|cycles? vary|var(?:y|ies) by|fund-specific|region(?:al)? deadlines?|multiple .* cycles|category-specific|program-specific|local deadlines?)\b/i.test(raw)) {
    return { type: "variable", label: "Deadlines vary by program", detail: raw, date: null };
  }
  if (/\b(tax years?|program years?|operates? from|active through|reauthorized through|fiscal year|incentive year|funding availability applies)\b/i.test(raw)) {
    return { type: "active_period", label: "Active program period", detail: raw, date: null };
  }
  if (/\b(recurring|annual|biennial|two-year cycle|periodic|quarterly|monthly|spring cycle|summer cycle|fall cycle|winter cycle|grant cycle|application cycle|competitive rounds?)\b/i.test(`${status} ${raw}`)) {
    return { type: "recurring", label: "Recurring cycle / next date pending", detail: raw, date: null };
  }
  return { type: "date_pending", label: "Next deadline not announced", detail: raw || "Check the official program page.", date: null };
}


  return { parseDeadline, fundingTiming };
}));
