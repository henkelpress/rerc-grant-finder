(function () {
  "use strict";

  const SCHEMA_VERSION = 1;
  const DB_NAME = "rerc-community-planner";
  const DB_VERSION = 1;
  const WORKSPACE_STORE = "workspaces";
  const GEOCODE_STORE = "geocodeCache";
  const DEFAULT_WORKSPACE_ID = "local";
  const LANGUAGE_KEY = "rerc.language";
  const LAST_WORKSPACE_KEY = "rerc.lastWorkspaceId";
  const MAX_IDS = 100;
  const MAX_COMPARE = 3;
  const MAX_NOTES = 12000;
  const MAX_FILE_BYTES = 256 * 1024;
  const MAX_SHARE_LENGTH = 1800;
  const INSTALLER_URL =
    "https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe";
  const PHASES = ["Plan", "Design", "Build", "Operate"];
  const ALLOWED_LANGUAGES = ["en", "es"];

  const TEXT = {
    en: {
      saved: "Saved",
      save: "Save",
      remove: "Remove",
      compare: "Compare",
      comparing: "Comparing",
      savedOnly: "Show saved only",
      allMatches: "Show all matches",
      noSaved: "No items saved yet.",
      noDeadlines: "No reviewed deadlines were found in the saved plan.",
      noProfile: "Choose a community and load its public profile.",
      profileUnavailable: "No public profile was found for this community.",
      profileLoaded: "Community profile loaded.",
      profileSource: "Source",
      profileVintage: "Data year",
      profileCoverage: "Coverage note",
      officialEnglish:
        "Official program names, rules, and source material may remain in English. Confirm requirements with the program.",
      plan: "Plan",
      design: "Design",
      build: "Build",
      operate: "Operate",
      whyMatch: "Why it matches",
      cautions: "Check before applying",
      dueSoon: "Due soon",
      dueToday: "Due today",
      pastDue: "Past date",
      daysLeft: "{days} days left",
      reviewedDeadline: "Reviewed deadline",
      openSource: "Open official source",
      compareTitle: "Compare saved options",
      compareLimit: "Choose up to three items to compare.",
      shareReady: "Private share link ready. Project title and notes are not included.",
      shareTooLong: "This selection is too large for a safe share link. Export a workspace file instead.",
      copied: "Link copied.",
      copyFailed: "Select and copy the link.",
      invalidWorkspace: "This workspace file is invalid or unsupported.",
      imported: "Workspace imported.",
      exported: "Workspace exported.",
      deleted: "Local workspace data deleted.",
      located: "Community location found.",
      locateFailed: "The community could not be located. Check the name and try again.",
      locateConsent:
        "The selected community is located automatically with OpenStreetMap Nominatim.",
      mapFallback: "Interactive map unavailable. Coordinates are shown as an accessible text fallback.",
      osmAttribution: "Map data © OpenStreetMap contributors",
      next: "Next",
      back: "Back",
      editProfile: "Edit profile",
      stepOf: "Step {step} of {total}",
      completePlace: "Choose a state or territory, place type, and community to continue.",
      calendarExported: "Calendar exported.",
      csvExported: "Saved-plan CSV exported.",
      docxExported: "Saved-plan Word document exported.",
      noExportItems: "Save at least one item before exporting a plan.",
      rercieExported: "RERC-e handoff exported.",
      includeNotes:
        "Include your project notes in the RERC-e handoff? The file stays on this computer unless you share it.",
      installerFallback: "If RERC-e is not installed, download the Windows installer.",
      projectWorkspace: "Community plan",
      communitySnapshot: "Community snapshot",
      roadmap: "Project roadmap",
      deadlines: "Reviewed deadlines",
      language: "Language",
      english: "English",
      spanish: "Español",
      savedCount: "{count} saved",
      compareCount: "{count} selected",
      unavailable: "Not listed",
      community: "Community",
      geography: "Geography",
      status: "Status",
      applicant: "Eligible applicants",
      stage: "Project stage",
      amount: "Amount or cost",
      match: "Match or cost share",
      deadline: "Deadline or availability",
      source: "Official source",
      type: "Type",
      organization: "Organization",
      title: "Title",
      notesExcluded: "Project title and notes are never placed in share links.",
      localOnly: "Saved on this device only.",
      explore: "Explore",
      filters: "Filters",
      myPlan: "My plan",
      choicesPage: "{label}: choices {start}-{end} of {total}",
      applicantChoices: "Applicant choices",
      topicChoices: "Topic choices",
    },
    es: {
      saved: "Guardado",
      save: "Guardar",
      remove: "Quitar",
      compare: "Comparar",
      comparing: "Comparando",
      savedOnly: "Mostrar solo lo guardado",
      allMatches: "Mostrar todos los resultados",
      noSaved: "Todavía no hay elementos guardados.",
      noDeadlines: "No se encontraron fechas revisadas en el plan guardado.",
      noProfile: "Elija una comunidad y cargue su perfil público.",
      profileUnavailable: "No se encontró un perfil público para esta comunidad.",
      profileLoaded: "Perfil de la comunidad cargado.",
      profileSource: "Fuente",
      profileVintage: "Año de los datos",
      profileCoverage: "Nota de cobertura",
      officialEnglish:
        "Los nombres, reglas y fuentes oficiales pueden permanecer en inglés. Confirme los requisitos con el programa.",
      plan: "Planificar",
      design: "Diseñar",
      build: "Construir",
      operate: "Operar",
      whyMatch: "Por qué coincide",
      cautions: "Revise antes de solicitar",
      dueSoon: "Vence pronto",
      dueToday: "Vence hoy",
      pastDue: "Fecha pasada",
      daysLeft: "Quedan {days} días",
      reviewedDeadline: "Fecha revisada",
      openSource: "Abrir fuente oficial",
      compareTitle: "Comparar opciones guardadas",
      compareLimit: "Elija hasta tres elementos para comparar.",
      shareReady: "Enlace privado listo. El título y las notas no están incluidos.",
      shareTooLong: "La selección es demasiado grande para un enlace seguro. Exporte el archivo del espacio de trabajo.",
      copied: "Enlace copiado.",
      copyFailed: "Seleccione y copie el enlace.",
      invalidWorkspace: "El archivo del espacio de trabajo no es válido o compatible.",
      imported: "Espacio de trabajo importado.",
      exported: "Espacio de trabajo exportado.",
      deleted: "Se borraron los datos locales.",
      located: "Se encontró la ubicación de la comunidad.",
      locateFailed: "No se pudo encontrar la comunidad. Revise el nombre e inténtelo de nuevo.",
      locateConsent:
        "La comunidad seleccionada se ubica automáticamente con OpenStreetMap Nominatim.",
      mapFallback: "El mapa interactivo no está disponible. Las coordenadas se muestran como texto accesible.",
      osmAttribution: "Datos del mapa © colaboradores de OpenStreetMap",
      next: "Siguiente",
      back: "Atrás",
      editProfile: "Editar perfil",
      stepOf: "Paso {step} de {total}",
      completePlace: "Elija un estado o territorio, un tipo de lugar y una comunidad para continuar.",
      calendarExported: "Calendario exportado.",
      csvExported: "CSV del plan exportado.",
      docxExported: "Documento Word del plan exportado.",
      noExportItems: "Guarde al menos un elemento antes de exportar el plan.",
      rercieExported: "Archivo para RERC-e exportado.",
      includeNotes:
        "¿Quiere incluir sus notas del proyecto en el archivo para RERC-e? El archivo permanece en este equipo a menos que lo comparta.",
      installerFallback: "Si RERC-e no está instalado, descargue el instalador para Windows.",
      projectWorkspace: "Plan comunitario",
      communitySnapshot: "Resumen de la comunidad",
      roadmap: "Ruta del proyecto",
      deadlines: "Fechas revisadas",
      language: "Idioma",
      english: "English",
      spanish: "Español",
      savedCount: "{count} guardados",
      compareCount: "{count} seleccionados",
      unavailable: "No indicado",
      community: "Comunidad",
      geography: "Geografía",
      status: "Estado",
      applicant: "Solicitantes elegibles",
      stage: "Etapa del proyecto",
      amount: "Monto o costo",
      match: "Aporte local",
      deadline: "Fecha o disponibilidad",
      source: "Fuente oficial",
      type: "Tipo",
      organization: "Organización",
      title: "Título",
      notesExcluded: "El título y las notas nunca se incluyen en enlaces compartidos.",
      localOnly: "Guardado solo en este dispositivo.",
      explore: "Explorar",
      filters: "Filtros",
      myPlan: "Mi plan",
      choicesPage: "{label}: opciones {start}-{end} de {total}",
      applicantChoices: "Opciones de solicitante",
      topicChoices: "Opciones de tema",
    },
  };

  const state = {
    db: null,
    workspace: null,
    language: "en",
    savedOnly: false,
    wizardStep: 1,
    map: null,
    marker: null,
    lastGeocodeAt: 0,
    saveTimer: null,
    observer: null,
  };
  const dialogOpeners = new WeakMap();

  function explorer() {
    return window.RERCExplorer || {};
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function t(key, variables) {
    let value = (TEXT[state.language] && TEXT[state.language][key]) || TEXT.en[key] || key;
    Object.keys(variables || {}).forEach(function (name) {
      value = value.replace("{" + name + "}", String(variables[name]));
    });
    return value;
  }

  function textValue(value, maxLength) {
    const limit = maxLength || 500;
    return typeof value === "string" ? value.trim().slice(0, limit) : "";
  }

  function catalog() {
    return Array.isArray(explorer().catalog) ? explorer().catalog : [];
  }

  function itemId(item) {
    return textValue(item && (item.item_id || item.id), 160);
  }

  function catalogMap() {
    const map = new Map();
    catalog().forEach(function (item) {
      const id = itemId(item);
      if (id) map.set(id, item);
    });
    return map;
  }

  function uniqueKnownIds(values, maximum) {
    const known = catalogMap();
    const output = [];
    (Array.isArray(values) ? values : []).forEach(function (value) {
      const id = textValue(value, 160);
      if (id && known.has(id) && !output.includes(id) && output.length < maximum) output.push(id);
    });
    return output;
  }

  function defaultWorkspace(id) {
    return {
      schema: SCHEMA_VERSION,
      id: textValue(id, 80) || DEFAULT_WORKSPACE_ID,
      savedIds: [],
      compareIds: [],
      roadmapAssignments: {},
      projectTitle: "",
      projectNotes: "",
      profile: {},
      updatedAt: new Date().toISOString(),
    };
  }

  function sanitizeProfile(profile) {
    const source = profile && typeof profile === "object" && !Array.isArray(profile) ? profile : {};
    const output = {};
    const stringFields = [
      "geoid",
      "name",
      "community",
      "state",
      "stateCode",
      "county",
      "placeType",
      "source",
      "vintage",
      "coverageNote",
      "populationLabel",
      "medianIncomeLabel",
      "povertyLabel",
      "broadbandLabel",
    ];
    stringFields.forEach(function (field) {
      const value = textValue(source[field], field === "coverageNote" ? 800 : 240);
      if (value) output[field] = value;
    });
    ["population", "medianHouseholdIncome", "povertyRate", "broadbandRate"].forEach(function (field) {
      const value = Number(source[field]);
      if (Number.isFinite(value)) output[field] = value;
    });
    const latitude = Number(source.latitude);
    const longitude = Number(source.longitude);
    if (Number.isFinite(latitude) && latitude >= -90 && latitude <= 90) output.latitude = latitude;
    if (Number.isFinite(longitude) && longitude >= -180 && longitude <= 180) output.longitude = longitude;
    return output;
  }

  function sanitizeWorkspace(input, strict) {
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("workspace-object");
    if (Number(input.schema) !== SCHEMA_VERSION) throw new Error("workspace-version");
    const allowed = new Set([
      "schema",
      "id",
      "savedIds",
      "compareIds",
      "roadmapAssignments",
      "projectTitle",
      "projectNotes",
      "profile",
      "updatedAt",
      "catalogVersion",
      "exportedAt",
    ]);
    if (strict && Object.keys(input).some(function (key) { return !allowed.has(key); })) {
      throw new Error("workspace-fields");
    }
    if (!Array.isArray(input.savedIds) || input.savedIds.length > MAX_IDS) throw new Error("workspace-saved");
    if (!Array.isArray(input.compareIds) || input.compareIds.length > MAX_COMPARE) {
      throw new Error("workspace-compare");
    }
    if (typeof input.projectNotes !== "string" || input.projectNotes.length > MAX_NOTES) {
      throw new Error("workspace-notes");
    }
    if (typeof input.projectTitle !== "string" || input.projectTitle.length > 200) {
      throw new Error("workspace-title");
    }
    if (!input.roadmapAssignments || typeof input.roadmapAssignments !== "object" ||
        Array.isArray(input.roadmapAssignments)) {
      throw new Error("workspace-roadmap");
    }

    const savedIds = uniqueKnownIds(input.savedIds, MAX_IDS);
    if (strict && savedIds.length !== input.savedIds.length) throw new Error("workspace-unknown-id");
    const compareIds = uniqueKnownIds(input.compareIds, MAX_COMPARE).filter(function (id) {
      return savedIds.includes(id);
    });
    if (strict && compareIds.length !== input.compareIds.length) throw new Error("workspace-compare-id");
    const assignments = {};
    Object.keys(input.roadmapAssignments).forEach(function (id) {
      const phase = input.roadmapAssignments[id];
      if (savedIds.includes(id) && PHASES.includes(phase)) assignments[id] = phase;
      else if (strict) throw new Error("workspace-roadmap-value");
    });
    return {
      schema: SCHEMA_VERSION,
      id: textValue(input.id, 80) || DEFAULT_WORKSPACE_ID,
      savedIds: savedIds,
      compareIds: compareIds,
      roadmapAssignments: assignments,
      projectTitle: textValue(input.projectTitle, 200),
      projectNotes: input.projectNotes.trim().slice(0, MAX_NOTES),
      profile: sanitizeProfile(input.profile),
      updatedAt: new Date().toISOString(),
    };
  }

  function openDatabase() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) {
        reject(new Error("indexeddb-unavailable"));
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains(WORKSPACE_STORE)) {
          db.createObjectStore(WORKSPACE_STORE, { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains(GEOCODE_STORE)) {
          db.createObjectStore(GEOCODE_STORE, { keyPath: "query" });
        }
      };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-open")); };
    });
  }

  function dbGet(storeName, key) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readonly").objectStore(storeName).get(key);
      request.onsuccess = function () { resolve(request.result || null); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-read")); };
    });
  }

  function dbPut(storeName, value) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readwrite").objectStore(storeName).put(value);
      request.onsuccess = function () { resolve(value); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-write")); };
    });
  }

  function dbClear(storeName) {
    return new Promise(function (resolve, reject) {
      const request = state.db.transaction(storeName, "readwrite").objectStore(storeName).clear();
      request.onsuccess = function () { resolve(); };
      request.onerror = function () { reject(request.error || new Error("indexeddb-clear")); };
    });
  }

  async function persistWorkspace() {
    state.workspace.updatedAt = new Date().toISOString();
    await dbPut(WORKSPACE_STORE, state.workspace);
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    dispatchUpdate();
  }

  function schedulePersist() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(function () {
      persistWorkspace().catch(reportError);
    }, 250);
  }

  function dispatchUpdate() {
    document.dispatchEvent(new CustomEvent("rerc:workspace-updated", {
      detail: {
        savedCount: state.workspace.savedIds.length,
        compareCount: state.workspace.compareIds.length,
        updatedAt: state.workspace.updatedAt,
      },
    }));
    refreshIcons();
  }

  function refreshIcons() {
    try {
      if (window.lucide && typeof window.lucide.createIcons === "function") {
        window.lucide.createIcons();
      }
    } catch (error) {
      console.warn("RERC planner icon refresh failed.", error);
    }
  }

  function reportError(error) {
    console.error("RERC planner:", error);
  }

  function setStatus(id, message, kind) {
    const element = byId(id);
    if (!element) return;
    element.textContent = message || "";
    element.dataset.status = kind || "info";
  }

  function createButton(label, action, item, active) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.action = action;
    button.dataset.itemId = itemId(item);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.className = "planner-card-action" + (active ? " active" : "");
    button.textContent = label;
    return button;
  }

  function syncActionButton(button, label, active) {
    const pressed = active ? "true" : "false";
    if (button.getAttribute("aria-pressed") !== pressed) button.setAttribute("aria-pressed", pressed);
    button.classList.toggle("active", active);
    if (button.textContent !== label) button.textContent = label;
  }
  function inferCardItem(card) {
    const known = catalogMap();
    const directId =
      card.dataset.itemId ||
      (card.querySelector("[data-item-id]") && card.querySelector("[data-item-id]").dataset.itemId);
    if (directId && known.has(directId)) return known.get(directId);

    const source = card.querySelector('a[href^="http"]');
    if (source) {
      const href = source.href.replace(/\/$/, "");
      const match = catalog().find(function (item) {
        return textValue(item.source_url, 1000).replace(/\/$/, "") === href;
      });
      if (match) return match;
    }

    const heading = card.querySelector("h2, h3, h4");
    if (heading) {
      const title = heading.textContent.trim();
      return catalog().find(function (item) { return textValue(item.title, 500) === title; }) || null;
    }
    return null;
  }

  function decorateResults() {
    const root = (explorer().elements && explorer().elements.results) || byId("results");
    if (!root || state.savedOnly) return;
    root.querySelectorAll("article, .result-card, [data-result-card]").forEach(function (card) {
      const item = inferCardItem(card);
      if (!item) return;
      const id = itemId(item);
      card.dataset.itemId = id;
      let actions = card.querySelector(".planner-card-actions");
      if (!actions) {
        actions = document.createElement("div");
        actions.className = "planner-card-actions";
        card.appendChild(actions);
      }
      const saved = state.workspace.savedIds.includes(id);
      const compared = state.workspace.compareIds.includes(id);
      let saveButton = actions.querySelector('[data-action="planner-save"]');
      if (!saveButton) {
        saveButton = createButton(saved ? t("remove") : t("save"), "planner-save", item, saved);
        actions.appendChild(saveButton);
      } else {
        syncActionButton(saveButton, saved ? t("remove") : t("save"), saved);
      }
      let compareButton = actions.querySelector('[data-action="planner-compare"]');
      if (!compareButton) {
        compareButton = createButton(compared ? t("comparing") : t("compare"), "planner-compare", item, compared);
        actions.appendChild(compareButton);
      } else {
        syncActionButton(compareButton, compared ? t("comparing") : t("compare"), compared);
      }
    });
  }

  function evidenceFor(item) {
    try {
      const raw = typeof explorer().matchEvidence === "function"
        ? explorer().matchEvidence(item)
        : null;
      if (Array.isArray(raw)) return { reasons: raw.map(String), cautions: [] };
      if (raw && typeof raw === "object") {
        return {
          reasons: (raw.reasons || raw.matches || raw.evidence || []).map(String),
          cautions: (raw.cautions || raw.warnings || []).map(String),
        };
      }
      if (typeof raw === "string" && raw.trim()) return { reasons: [raw.trim()], cautions: [] };
    } catch (error) {
      reportError(error);
    }
    const fallback = textValue(item.why_it_matters || item.summary, 800);
    return { reasons: fallback ? [fallback] : [], cautions: [] };
  }

  function summaryFor(item) {
    try {
      if (typeof explorer().publicSummary === "function") {
        const value = explorer().publicSummary(item);
        if (typeof value === "string") return value;
        if (value && typeof value.summary === "string") return value.summary;
      }
    } catch (error) {
      reportError(error);
    }
    return textValue(item.summary, 1200);
  }

  function appendEvidence(parent, item) {
    const evidence = evidenceFor(item);
    if (evidence.reasons.length) {
      const title = document.createElement("strong");
      title.textContent = t("whyMatch") + ": ";
      parent.appendChild(title);
      parent.appendChild(document.createTextNode(evidence.reasons.join(" ")));
    }
    if (evidence.cautions.length) {
      const caution = document.createElement("p");
      const title = document.createElement("strong");
      title.textContent = t("cautions") + ": ";
      caution.appendChild(title);
      caution.appendChild(document.createTextNode(evidence.cautions.join(" ")));
      parent.appendChild(caution);
    }
  }

  function createSavedCard(item, compact) {
    const id = itemId(item);
    const card = document.createElement("article");
    card.className = compact ? "saved-tray-item" : "result-card planner-saved-card";
    card.dataset.itemId = id;

    const heading = document.createElement(compact ? "h4" : "h3");
    heading.textContent = textValue(item.title, 500) || t("unavailable");
    card.appendChild(heading);

    const meta = document.createElement("p");
    meta.className = "result-meta";
    meta.textContent = [
      textValue(item.item_type, 80),
      textValue(item.organization, 300),
      textValue(item.status, 120),
    ].filter(Boolean).join(" · ");
    card.appendChild(meta);

    if (!compact) {
      const summary = document.createElement("p");
      summary.textContent = summaryFor(item);
      card.appendChild(summary);
      const evidence = document.createElement("p");
      evidence.className = "match-evidence";
      appendEvidence(evidence, item);
      card.appendChild(evidence);
      const source = safeAnchor(item.source_url, t("openSource"));
      if (source) card.appendChild(source);
    }

    const actions = document.createElement("div");
    actions.className = "planner-card-actions";
    actions.appendChild(createButton(t("remove"), "planner-save", item, true));
    actions.appendChild(createButton(
      state.workspace.compareIds.includes(id) ? t("comparing") : t("compare"),
      "planner-compare",
      item,
      state.workspace.compareIds.includes(id)
    ));
    card.appendChild(actions);
    return card;
  }

  function renderSavedOnly() {
    const root = (explorer().elements && explorer().elements.results) || byId("results");
    if (!root) return;
    root.replaceChildren();
    const items = savedItems();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = t("noSaved");
      root.appendChild(empty);
      return;
    }
    items.forEach(function (item) { root.appendChild(createSavedCard(item, false)); });
  }

  function renderSavedTray() {
    const root = byId("savedTrayItems");
    if (!root) return;
    root.replaceChildren();
    const items = savedItems();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.textContent = t("noSaved");
      root.appendChild(empty);
    } else {
      items.forEach(function (item) { root.appendChild(createSavedCard(item, true)); });
    }
    setCount("savedTrayCount", items.length, "savedCount");
  }

  function setCount(id, count, key) {
    const element = byId(id);
    if (!element) return;
    element.textContent = String(count);
    element.setAttribute("aria-label", t(key, { count: count }));
  }

  function savedItems() {
    const known = catalogMap();
    return state.workspace.savedIds.map(function (id) { return known.get(id); }).filter(Boolean);
  }

  async function toggleSaved(id) {
    const index = state.workspace.savedIds.indexOf(id);
    if (index >= 0) {
      state.workspace.savedIds.splice(index, 1);
      state.workspace.compareIds = state.workspace.compareIds.filter(function (value) { return value !== id; });
      delete state.workspace.roadmapAssignments[id];
    } else if (state.workspace.savedIds.length < MAX_IDS && catalogMap().has(id)) {
      state.workspace.savedIds.push(id);
      state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
    }
    await persistWorkspace();
    refreshWorkspaceUI();
  }

  async function toggleCompare(id) {
    if (!state.workspace.savedIds.includes(id)) {
      if (state.workspace.savedIds.length >= MAX_IDS) return;
      state.workspace.savedIds.push(id);
      state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
    }
    const index = state.workspace.compareIds.indexOf(id);
    if (index >= 0) {
      state.workspace.compareIds.splice(index, 1);
    } else if (state.workspace.compareIds.length < MAX_COMPARE) {
      state.workspace.compareIds.push(id);
    } else {
      setStatus("shareStatus", t("compareLimit"), "warning");
      return;
    }
    await persistWorkspace();
    refreshWorkspaceUI();
  }

  function inferPhase(item) {
    const stage = textValue(item && item.project_stage, 300).toLowerCase();
    if (/design|engineering|predevelopment/.test(stage)) return "Design";
    if (/construct|implement|acquisition|capital|build/.test(stage)) return "Build";
    if (/operat|maint|capacity|workforce|business/.test(stage)) return "Operate";
    return "Plan";
  }

  function renderRoadmap() {
    const root = byId("roadmap");
    if (!root) return;
    root.replaceChildren();
    const groups = {};
    PHASES.forEach(function (phase) { groups[phase] = []; });
    savedItems().forEach(function (item) {
      const id = itemId(item);
      const phase = PHASES.includes(state.workspace.roadmapAssignments[id])
        ? state.workspace.roadmapAssignments[id]
        : inferPhase(item);
      groups[phase].push(item);
    });

    PHASES.forEach(function (phase) {
      const section = document.createElement("section");
      section.className = "roadmap-phase";
      const heading = document.createElement("h3");
      heading.textContent = t(phase.toLowerCase());
      section.appendChild(heading);
      if (!groups[phase].length) {
        const empty = document.createElement("p");
        empty.textContent = "0";
        empty.className = "roadmap-empty";
        section.appendChild(empty);
      }
      groups[phase].forEach(function (item) {
        const row = document.createElement("div");
        row.className = "roadmap-item";
        const label = document.createElement("label");
        const selectId = "roadmap-" + cssSafeId(itemId(item));
        label.htmlFor = selectId;
        label.textContent = textValue(item.title, 500);
        const select = document.createElement("select");
        select.id = selectId;
        select.dataset.roadmapId = itemId(item);
        select.setAttribute("aria-label", textValue(item.title, 500) + " phase");
        PHASES.forEach(function (value) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = t(value.toLowerCase());
          option.selected = value === phase;
          select.appendChild(option);
        });
        row.append(label, select);
        section.appendChild(row);
      });
      root.appendChild(section);
    });
    setCount("roadmapCount", state.workspace.savedIds.length, "savedCount");
  }

  function cssSafeId(value) {
    return String(value).replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 100);
  }

  function reviewedDeadline(item) {
    if (typeof explorer().parseDeadline !== "function") return null;
    try {
      const parsed = explorer().parseDeadline(item);
      if (!parsed || typeof parsed !== "object") return null;
      if (parsed instanceof Date) {
        if (Number.isNaN(parsed.getTime())) return null;
        return {
          date: parsed,
          kind: "reviewed",
          source: textValue(item.source_url, 1000),
          reviewedAt: textValue(item.last_checked, 80),
        };
      }
      const reviewed =
        parsed.reviewed === true ||
        parsed.isReviewed === true ||
        parsed.status === "reviewed" ||
        parsed.confidence === "reviewed";
      if (!reviewed) return null;
      const candidate = parsed.date || parsed.closesOn || parsed.closes_on || parsed.iso || parsed.value;
      const date = candidate instanceof Date ? candidate : new Date(candidate);
      if (Number.isNaN(date.getTime())) return null;
      return {
        date: date,
        kind: textValue(parsed.kind || parsed.deadlineKind, 80),
        source: textValue(parsed.source || item.source_url, 1000),
        reviewedAt: textValue(parsed.reviewedAt || parsed.reviewed_at || item.last_checked, 80),
      };
    } catch (error) {
      reportError(error);
      return null;
    }
  }

  function deadlineLabel(date) {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const due = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const days = Math.round((due.getTime() - start.getTime()) / 86400000);
    if (days < 0) return { text: t("pastDue"), kind: "past" };
    if (days === 0) return { text: t("dueToday"), kind: "urgent" };
    if (days <= 30) return { text: t("dueSoon") + " · " + t("daysLeft", { days: days }), kind: "soon" };
    return { text: t("daysLeft", { days: days }), kind: "future" };
  }

  function deadlineItems() {
    return savedItems().map(function (item) {
      const deadline = reviewedDeadline(item);
      return deadline ? { item: item, deadline: deadline } : null;
    }).filter(Boolean).sort(function (a, b) {
      return a.deadline.date.getTime() - b.deadline.date.getTime();
    });
  }

  function renderDeadlines() {
    const root = byId("deadlineList");
    if (!root) return;
    root.replaceChildren();
    const deadlines = deadlineItems();
    if (!deadlines.length) {
      const empty = document.createElement("p");
      empty.textContent = t("noDeadlines");
      root.appendChild(empty);
      return;
    }
    deadlines.forEach(function (entry) {
      const row = document.createElement("article");
      row.className = "deadline-item";
      const heading = document.createElement("h3");
      heading.textContent = textValue(entry.item.title, 500);
      const date = document.createElement("time");
      date.dateTime = isoDate(entry.deadline.date);
      date.textContent = new Intl.DateTimeFormat(state.language, {
        year: "numeric",
        month: "long",
        day: "numeric",
      }).format(entry.deadline.date);
      const badge = document.createElement("span");
      const label = deadlineLabel(entry.deadline.date);
      badge.className = "deadline-label " + label.kind;
      badge.textContent = label.text;
      const reviewed = document.createElement("small");
      reviewed.textContent = [t("reviewedDeadline"), entry.deadline.reviewedAt].filter(Boolean).join(" · ");
      row.append(heading, date, badge, reviewed);
      root.appendChild(row);
    });
  }

  function renderComparison() {
    const tableRoot = byId("comparisonTable");
    if (!tableRoot) return;
    tableRoot.replaceChildren();
    const known = catalogMap();
    const items = state.workspace.compareIds.map(function (id) { return known.get(id); }).filter(Boolean);
    if (!items.length) {
      const empty = document.createElement("p");
      empty.textContent = t("compareLimit");
      tableRoot.appendChild(empty);
      return;
    }
    const table = document.createElement("table");
    const caption = document.createElement("caption");
    caption.textContent = t("compareTitle");
    table.appendChild(caption);
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    const emptyHead = document.createElement("th");
    emptyHead.scope = "col";
    headRow.appendChild(emptyHead);
    items.forEach(function (item) {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = textValue(item.title, 500);
      headRow.appendChild(th);
    });
    head.appendChild(headRow);
    table.appendChild(head);
    const body = document.createElement("tbody");
    [
      ["type", "item_type"],
      ["organization", "organization"],
      ["status", "status"],
      ["geography", "geography"],
      ["applicant", "eligible_users"],
      ["stage", "project_stage"],
      ["amount", "amount_or_cost"],
      ["match", "match_or_cost"],
      ["deadline", "deadline_or_availability"],
    ].forEach(function (definition) {
      const row = document.createElement("tr");
      const label = document.createElement("th");
      label.scope = "row";
      label.textContent = t(definition[0]);
      row.appendChild(label);
      items.forEach(function (item) {
        const cell = document.createElement("td");
        cell.textContent = textValue(item[definition[1]], 2000) || t("unavailable");
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    const evidenceRow = document.createElement("tr");
    const evidenceLabel = document.createElement("th");
    evidenceLabel.scope = "row";
    evidenceLabel.textContent = t("whyMatch");
    evidenceRow.appendChild(evidenceLabel);
    items.forEach(function (item) {
      const cell = document.createElement("td");
      const evidence = evidenceFor(item);
      cell.textContent = evidence.reasons.join(" ") || t("unavailable");
      evidenceRow.appendChild(cell);
    });
    body.appendChild(evidenceRow);
    table.appendChild(body);
    tableRoot.appendChild(table);
  }

  function refreshCounts() {
    const saved = state.workspace.savedIds.length;
    const compared = state.workspace.compareIds.length;
    ["savedCountBadge", "mobileSavedCount", "savedTrayCount"].forEach(function (id) {
      setCount(id, saved, "savedCount");
    });
    ["compareCountBadge"].forEach(function (id) {
      setCount(id, compared, "compareCount");
    });
    const openCompare = byId("openCompare");
    if (openCompare) openCompare.disabled = compared === 0;
    const compareSaved = byId("compareSaved");
    if (compareSaved) compareSaved.disabled = compared === 0;
  }

  function refreshWorkspaceUI() {
    refreshCounts();
    renderSavedTray();
    renderRoadmap();
    renderDeadlines();
    renderComparison();
    renderCommunitySnapshot();
    if (state.savedOnly) renderSavedOnly();
    else decorateResults();
    syncSavedOnlyControl();
    refreshIcons();
  }

  function syncSavedOnlyControl() {
    const control = byId("showSavedOnly");
    if (!control) return;
    if ("checked" in control) control.checked = state.savedOnly;
    control.setAttribute("aria-pressed", state.savedOnly ? "true" : "false");
    if (control.tagName === "BUTTON") {
      control.textContent = state.savedOnly ? t("allMatches") : t("savedOnly");
    }
  }

  function toggleSavedOnly(force) {
    state.savedOnly = typeof force === "boolean" ? force : !state.savedOnly;
    if (state.savedOnly) {
      renderSavedOnly();
    } else if (typeof explorer().render === "function") {
      explorer().render();
      window.requestAnimationFrame(decorateResults);
    }
    syncSavedOnlyControl();
  }

  function openDialog(id) {
    const dialog = byId(id);
    if (!dialog) return;
    const opener = document.activeElement;
    if (opener instanceof HTMLElement && !dialog.contains(opener)) dialogOpeners.set(dialog, opener);
    if (typeof dialog.showModal === "function") dialog.showModal();
    else {
      dialog.hidden = false;
      dialog.setAttribute("open", "");
    }
    const focusable = dialog.querySelector("button, input, select, textarea, a[href]");
    if (focusable) focusable.focus();
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else {
      dialog.hidden = true;
      dialog.removeAttribute("open");
    }
    const opener = dialogOpeners.get(dialog);
    dialogOpeners.delete(dialog);
    if (opener && opener.isConnected) window.requestAnimationFrame(function () { opener.focus(); });
  }

  function revealCommunityForm(focusMissing) {
    const filters = byId("communityFilters");
    const toggle = byId("toggleFilters");
    if (filters) {
      filters.hidden = false;
      filters.classList.add("open");
      filters.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (toggle) {
      toggle.setAttribute("aria-expanded", "true");
      const label = toggle.querySelector("span");
      if (label) label.textContent = "Hide community questions";
    }
    if (typeof state.showWizardStep === "function") state.showWizardStep(1, { focus: false });
    if (focusMissing) {
      const name = byId("communityName");
      const stateSelect = byId("stateSelect");
      const placeType = byId("placeTypeSelect");
      const target = stateSelect && !stateSelect.value
        ? stateSelect
        : (placeType && !placeType.value ? placeType : name);
      if (target) window.requestAnimationFrame(function () { target.focus({ preventScroll: true }); });
    }
  }

  function syncCommunityGate() {
    const ready = hasPlaceSelection();
    document.documentElement.classList.toggle("community-ready", ready);
    document.querySelectorAll("[data-community-gated]").forEach(function (section) {
      section.hidden = !ready;
      section.setAttribute("aria-hidden", ready ? "false" : "true");
    });
    document.querySelectorAll("#workflowSteps [data-wizard-step]").forEach(function (button) {
      const step = Number(button.dataset.wizardStep || 1);
      button.disabled = !ready && step > 1;
      button.setAttribute("aria-disabled", button.disabled ? "true" : "false");
    });
    if (ready) {
      const name = byId("communityName");
      const stateSelect = byId("stateSelect");
      const placeType = byId("placeTypeSelect");
      [stateSelect, placeType, name].forEach(function (control) {
        if (!control) return;
        control.setCustomValidity("");
        control.removeAttribute("aria-invalid");
      });
    }
    return ready;
  }

  function requireCommunityInfo() {
    if (syncCommunityGate()) return true;
    const stateSelect = byId("stateSelect");
    const placeType = byId("placeTypeSelect");
    const name = byId("communityName");
    const message = t("completePlace");
    const controls = [stateSelect, placeType, name];
    controls.forEach(function (control) {
      if (!control) return;
      const missing = !control.value;
      control.setCustomValidity(missing ? message : "");
      if (missing) control.setAttribute("aria-invalid", "true");
      else control.removeAttribute("aria-invalid");
    });
    setStatus("profileStatus", message, "warning");
    revealCommunityForm(true);
    const firstMissing = controls.find(function (control) { return control && !control.value; });
    if (firstMissing && typeof firstMissing.reportValidity === "function") firstMissing.reportValidity();
    return false;
  }
  function setupWizard() {
    const root = byId("workflowSteps");
    const form = byId("communityFilters");
    if (!root || !form) return;
    const stepButtons = Array.from(root.querySelectorAll("[data-wizard-step], [data-step]"));
    const panels = Array.from(document.querySelectorAll("[data-wizard-panel]"));
    const total = Math.max(stepButtons.length, 4);
    let controls = form.querySelector(".wizard-controls");
    if (!controls) {
      controls = document.createElement("div");
      controls.className = "wizard-controls";
      const back = document.createElement("button");
      back.type = "button";
      back.dataset.wizardBack = "";
      back.textContent = t("back");
      const next = document.createElement("button");
      next.type = "button";
      next.dataset.wizardNext = "";
      next.textContent = t("next");
      controls.append(back, next);
      form.appendChild(controls);
    }

    function showStep(nextStep, options) {
      const requested = Math.min(Math.max(Number(nextStep) || 1, 1), total);
      if (requested > 1 && !requireCommunityInfo()) return false;
      state.wizardStep = requested;
      stepButtons.forEach(function (button, index) {
        const step = Number(button.dataset.wizardStep || button.dataset.step || index + 1);
        const active = step === state.wizardStep;
        button.setAttribute("aria-current", active ? "step" : "false");
        button.classList.toggle("active", active);
      });
      panels.forEach(function (panel, index) {
        const step = Number(panel.dataset.wizardPanel || index + 1);
        panel.hidden = step !== state.wizardStep;
      });
      form.hidden = state.wizardStep >= 3;
      root.setAttribute("aria-label", t("stepOf", { step: state.wizardStep, total: total }));
      root.dataset.currentStep = String(state.wizardStep);
      const back = controls.querySelector("[data-wizard-back]");
      const next = controls.querySelector("[data-wizard-next]");
      if (back) back.hidden = state.wizardStep <= 1;
      if (next) next.hidden = state.wizardStep >= 3;
      if (state.wizardStep >= 3) {
        captureProfileFromFilters();
        if (typeof explorer().render === "function") explorer().render();
        const destination = byId(state.wizardStep === 4 ? "planWorkspace" : "matchesWorkspace");
        if (destination) {
          destination.hidden = false;
          destination.setAttribute("aria-hidden", "false");
          destination.scrollIntoView({ behavior: "smooth", block: "start" });
          if (!options || options.focus !== false) destination.focus({ preventScroll: true });
        }
      }
      syncCommunityGate();
      return true;
    }

    function handleNavigation(event) {
      const target = event.target.closest("[data-wizard-step], [data-step], [data-wizard-next], [data-wizard-back]");
      if (!target) return;
      event.preventDefault();
      if (target.hasAttribute("data-wizard-next")) showStep(state.wizardStep + 1);
      else if (target.hasAttribute("data-wizard-back")) showStep(state.wizardStep - 1);
      else showStep(target.dataset.wizardStep || target.dataset.step);
    }

    root.addEventListener("click", handleNavigation);
    form.addEventListener("click", handleNavigation);
    state.showWizardStep = showStep;
    showStep(1, { focus: false });
  }

  function choiceItems(root) {
    return Array.from(root.children).filter(function (child) {
      return child.matches("label, .check-option, .choice-option") ||
        Boolean(child.querySelector('input[type="checkbox"], input[type="radio"]'));
    });
  }

  function setupChoicePager(rootId, labelKey) {
    const root = byId(rootId);
    if (!root || root.dataset.choicePagerReady === "true") return;
    const choices = choiceItems(root);
    if (choices.length <= 6) return;
    root.dataset.choicePagerReady = "true";
    root.dataset.choicePage = "0";
    root.dataset.choiceLabelKey = labelKey;

    const status = document.createElement("p");
    status.className = "choice-pager-status";
    status.setAttribute("aria-live", "polite");
    const controls = document.createElement("div");
    controls.className = "choice-pager-controls";
    const back = document.createElement("button");
    back.type = "button";
    back.dataset.choiceBack = rootId;
    back.textContent = t("back");
    const next = document.createElement("button");
    next.type = "button";
    next.dataset.choiceNext = rootId;
    next.textContent = t("next");
    controls.append(back, status, next);
    root.after(controls);

    function showPage(page) {
      const totalPages = Math.ceil(choices.length / 6);
      const current = Math.min(Math.max(Number(page) || 0, 0), totalPages - 1);
      const start = current * 6;
      const end = Math.min(start + 6, choices.length);
      root.dataset.choicePage = String(current);
      choices.forEach(function (choice, index) {
        choice.hidden = index < start || index >= end;
      });
      back.disabled = current === 0;
      next.disabled = current === totalPages - 1;
      status.textContent = t("choicesPage", {
        label: t(labelKey),
        start: start + 1,
        end: end,
        total: choices.length,
      });
    }

    controls.addEventListener("click", function (event) {
      const button = event.target.closest("button");
      if (!button) return;
      const current = Number(root.dataset.choicePage || 0);
      showPage(button.hasAttribute("data-choice-back") ? current - 1 : current + 1);
      const visibleChoice = choices.find(function (choice) { return !choice.hidden; });
      const focusable = visibleChoice && visibleChoice.querySelector("input, button");
      if (focusable) focusable.focus();
    });
    showPage(0);
  }

  function mobileNavItem(label, icon, target, buttonAction) {
    const element = buttonAction ? document.createElement("button") : document.createElement("a");
    if (buttonAction) {
      element.type = "button";
      element.dataset.mobileAction = buttonAction;
    } else {
      element.href = target;
    }
    const iconElement = document.createElement("i");
    iconElement.dataset.lucide = icon;
    iconElement.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.textContent = label;
    element.append(iconElement, text);
    return element;
  }

  function setupMobileNavigation() {
    let nav = byId("plannerMobileNav") || document.querySelector(".mobile-nav");
    if (!nav) {
      nav = document.createElement("nav");
      nav.id = "plannerMobileNav";
      const explore = mobileNavItem(t("explore"), "search", "", "explore");
      explore.dataset.labelKey = "explore";
      const filters = mobileNavItem(t("filters"), "sliders-horizontal", "", "filters");
      filters.dataset.labelKey = "filters";
      const saved = mobileNavItem(t("saved"), "bookmark", "", "saved");
      saved.dataset.labelKey = "saved";
      const badge = document.createElement("span");
      badge.id = "mobileSavedCount";
      badge.className = "mobile-nav-badge";
      badge.textContent = String(state.workspace.savedIds.length);
      badge.setAttribute("aria-label", t("savedCount", { count: state.workspace.savedIds.length }));
      saved.appendChild(badge);
      const plan = mobileNavItem(t("myPlan"), "clipboard-list", "", "plan");
      plan.dataset.labelKey = "myPlan";
      nav.append(explore, filters, saved, plan);
      document.body.appendChild(nav);
    } else {
      nav.id = "plannerMobileNav";
      nav.querySelectorAll("a, button").forEach(function (item) {
        const href = item.getAttribute("href") || "";
        if (item.dataset.mobileAction === "saved") item.dataset.labelKey = "saved";
        else if (href === "#communityFilters") { item.dataset.labelKey = "filters"; item.dataset.mobileAction = "filters"; }
        else if (href === "#matchesWorkspace") { item.dataset.labelKey = "explore"; item.dataset.mobileAction = "explore"; }
        else if (href === "#planWorkspace") { item.dataset.labelKey = "myPlan"; item.dataset.mobileAction = "plan"; }
      });
    }
    nav.setAttribute("aria-label", t("projectWorkspace"));
    if (nav.dataset.plannerBound === "true") return;
    nav.dataset.plannerBound = "true";
    nav.addEventListener("click", function (event) {
      const action = event.target.closest("[data-mobile-action]");
      if (!action) return;
      const mobileAction = action.dataset.mobileAction;
      if (mobileAction === "filters") {
        event.preventDefault();
        revealCommunityForm(true);
        return;
      }
      if (mobileAction === "explore" || mobileAction === "plan") {
        event.preventDefault();
        if (!requireCommunityInfo()) return;
        if (typeof state.showWizardStep === "function") state.showWizardStep(mobileAction === "plan" ? 4 : 3);
        return;
      }
      if (mobileAction === "saved") {
        const tray = byId("savedTray");
        const toggle = byId("toggleSavedTray");
        if (tray) tray.hidden = false;
        if (toggle) toggle.setAttribute("aria-expanded", "true");
        renderSavedTray();
        if (tray) {
          tray.scrollIntoView({ behavior: "smooth", block: "start" });
          const firstAction = tray.querySelector("button, a");
          if (firstAction) firstAction.focus({ preventScroll: true });
        }
      }
    });
  }
  function hasPlaceSelection() {
    const name = byId("communityName");
    const stateSelect = byId("stateSelect");
    const placeType = byId("placeTypeSelect");
    return Boolean(stateSelect && stateSelect.value && placeType && placeType.value && name && name.value);
  }

  function selectedValues(root) {
    if (!root) return [];
    return Array.from(root.querySelectorAll('input[type="checkbox"]:checked, input[type="radio"]:checked'))
      .map(function (input) { return input.value; })
      .filter(Boolean);
  }

  function controlledFilters() {
    const values = {};
    ["stateSelect", "placeTypeSelect", "stageSelect", "sortSelect", "limitSelect"].forEach(function (id) {
      const element = byId(id);
      if (element && element.value) values[id] = textValue(element.value, 100);
    });
    ["applicantOptions", "topicOptions"].forEach(function (id) {
      const selected = selectedValues(byId(id)).map(function (value) { return textValue(value, 100); }).slice(0, 30);
      if (selected.length) values[id] = selected;
    });
    const includeClosed = byId("includeClosed");
    if (includeClosed) values.includeClosed = Boolean(includeClosed.checked);
    const modeButton = document.querySelector("[data-mode][aria-pressed='true']");
    if (modeButton) values.mode = textValue(modeButton.dataset.mode, 40);
    return values;
  }

  function applyControlledFilters(filters) {
    if (!filters || typeof filters !== "object") return;
    ["stateSelect", "placeTypeSelect", "stageSelect", "sortSelect", "limitSelect"].forEach(function (id) {
      const element = byId(id);
      const value = textValue(filters[id], 100);
      if (element && value && Array.from(element.options || []).some(function (option) { return option.value === value; })) {
        element.value = value;
      }
    });
    ["applicantOptions", "topicOptions"].forEach(function (id) {
      const allowed = Array.isArray(filters[id]) ? filters[id].map(String) : [];
      const root = byId(id);
      if (root) {
        root.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(function (input) {
          input.checked = allowed.includes(input.value);
        });
      }
    });
    const includeClosed = byId("includeClosed");
    if (includeClosed && typeof filters.includeClosed === "boolean") includeClosed.checked = filters.includeClosed;
    if (filters.mode && typeof explorer().chooseMode === "function") {
      explorer().chooseMode(textValue(filters.mode, 40));
    }
  }

  function captureProfileFromFilters() {
    const stateSelect = byId("stateSelect");
    const placeType = byId("placeTypeSelect");
    const selected = typeof explorer().getSelectedCommunityProfile === "function"
      ? explorer().getSelectedCommunityProfile()
      : null;
    const profile = selected ? Object.assign({}, selected) : {};
    if (selected && typeof explorer().getSelectedCommunityName === "function") {
      profile.community = explorer().getSelectedCommunityName();
      profile.name = profile.community;
    }
    if (stateSelect && stateSelect.value) {
      profile.state = stateSelect.options[stateSelect.selectedIndex]
        ? stateSelect.options[stateSelect.selectedIndex].text.trim().slice(0, 120)
        : stateSelect.value.slice(0, 120);
      profile.stateCode = stateSelect.value.slice(0, 120);
    }
    if (placeType && placeType.value) profile.placeType = placeType.value.slice(0, 80);
    state.workspace.profile = sanitizeProfile(profile);
    schedulePersist();
    renderProfileSummary();
  }
  function projectedProfiles() {
    const raw = window.RERC_COMMUNITY_PROFILES;
    if (Array.isArray(raw)) return raw;
    if (raw && typeof raw === "object") {
      return Object.keys(raw).map(function (key) {
        const value = raw[key];
        return value && typeof value === "object" ? Object.assign({ geoid: key }, value) : null;
      }).filter(Boolean);
    }
    return [];
  }

  function findProjectedProfile() {
    if (typeof explorer().getSelectedCommunityProfile === "function") {
      return explorer().getSelectedCommunityProfile();
    }
    const currentGeoid = textValue(state.workspace.profile.geoid, 80);
    return projectedProfiles().find(function (profile) {
      return currentGeoid && textValue(profile.geoid, 80) === currentGeoid;
    }) || null;
  }
  async function loadProjectedProfile() {
    if (!requireCommunityInfo()) return;
    captureProfileFromFilters();
    const projected = findProjectedProfile();
    if (!projected) {
      setStatus("profileStatus", t("profileUnavailable"), "warning");
      renderProfileSummary();
      return;
    }
    state.workspace.profile = sanitizeProfile(Object.assign({}, state.workspace.profile, projected));
    await persistWorkspace();
    setStatus("profileStatus", t("profileLoaded"), "success");
    renderProfileSummary();
    renderCommunitySnapshot();
    try {
      await locateCommunity();
    } catch (error) {
      renderMap();
      setStatus("mapStatus", t("locateFailed"), "warning");
      reportError(error);
    }
  }

  function profileRows(profile) {
    const rows = [];
    [
      ["community", profile.community || profile.name],
      ["geography", [profile.county, profile.state].filter(Boolean).join(", ")],
      ["profileSource", profile.source],
      ["profileVintage", profile.vintage],
      ["profileCoverage", profile.coverageNote],
    ].forEach(function (row) {
      if (row[1]) rows.push({ label: t(row[0]), value: String(row[1]) });
    });
    if (Number.isFinite(profile.population)) {
      rows.push({ label: "Population", value: new Intl.NumberFormat(state.language).format(profile.population) });
    } else if (profile.populationLabel) {
      rows.push({ label: "Population", value: profile.populationLabel });
    }
    if (Number.isFinite(profile.medianHouseholdIncome)) {
      rows.push({
        label: "Median household income",
        value: new Intl.NumberFormat(state.language, { style: "currency", currency: "USD", maximumFractionDigits: 0 })
          .format(profile.medianHouseholdIncome),
      });
    } else if (profile.medianIncomeLabel) {
      rows.push({ label: "Median household income", value: profile.medianIncomeLabel });
    }
    return rows;
  }

  function renderDefinitionList(root, rows) {
    root.replaceChildren();
    const list = document.createElement("dl");
    rows.forEach(function (row) {
      const wrapper = document.createElement("div");
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = row.label;
      description.textContent = row.value;
      wrapper.append(term, description);
      list.appendChild(wrapper);
    });
    root.appendChild(list);
  }

  function renderProfileSummary() {
    const section = byId("communityProfileSummary");
    if (section) section.hidden = false;
    const root = byId("profileSummaryContent");
    if (root) {
      const rows = profileRows(state.workspace.profile);
      if (rows.length) renderDefinitionList(root, rows);
      else {
        root.replaceChildren();
        const empty = document.createElement("p");
        empty.textContent = t("noProfile");
        root.appendChild(empty);
      }
      const notice = document.createElement("p");
      notice.className = "language-notice";
      notice.textContent = t("officialEnglish");
      root.appendChild(notice);
    }
    const priority = byId("prioritySummaryContent");
    if (priority) {
      priority.replaceChildren();
      const filters = controlledFilters();
      const topics = filters.topicOptions || [];
      const applicants = filters.applicantOptions || [];
      const summary = document.createElement("p");
      summary.textContent = [
        topics.length ? topics.join(", ") : "",
        applicants.length ? applicants.join(", ") : "",
        filters.stageSelect || "",
      ].filter(Boolean).join(" · ") || t("unavailable");
      priority.appendChild(summary);
    }
  }

  function renderCommunitySnapshot() {
    const root = byId("communitySnapshot");
    if (!root) return;
    const rows = profileRows(state.workspace.profile);
    if (!rows.length) {
      root.replaceChildren();
      const empty = document.createElement("p");
      empty.textContent = t("noProfile");
      root.appendChild(empty);
      return;
    }
    renderDefinitionList(root, rows);
    const note = document.createElement("p");
    note.className = "profile-limitations";
    note.textContent = state.workspace.profile.coverageNote || t("officialEnglish");
    root.appendChild(note);
  }

  function geocodeCountryCode() {
    // Nominatim returns U.S. territories under country_code=us; state validation keeps them distinct.
    return "us";
  }

  function geocodePlaceName() {
    const community = typeof explorer().getSelectedCommunityName === "function"
      ? explorer().getSelectedCommunityName()
      : "";
    return community
      .replace(/\s+(city|town|village|borough|municipality|municipio|subdistrict|zona urbana)$/i, "")
      .replace(/\s+CDP(?:\s+\([^)]*\))?$/i, "")
      .trim();
  }

  function geocodeStateName() {
    const selected = textValue(byId("stateSelect") && byId("stateSelect").value, 120);
    return {
      "U.S. Virgin Islands": "United States Virgin Islands",
      "Northern Mariana Islands": "Commonwealth of the Northern Mariana Islands",
    }[selected] || selected;
  }

  function geocodeQuery() {
    return [geocodePlaceName(), geocodeStateName(), "United States"].filter(Boolean).join(", ").slice(0, 300);
  }

  function expectedStateAliases() {
    const selected = textValue(byId("stateSelect") && byId("stateSelect").value, 120).toLowerCase();
    const aliases = {
      "u.s. virgin islands": ["u.s. virgin islands", "united states virgin islands", "virgin islands"],
      "northern mariana islands": ["northern mariana islands", "commonwealth of the northern mariana islands"],
    };
    return aliases[selected] || [selected];
  }

  function matchingGeocodeResult(results) {
    const stateAliases = expectedStateAliases();
    return results.find(function (candidate) {
      const address = candidate && candidate.address && typeof candidate.address === "object" ? candidate.address : {};
      const stateName = textValue(address.state || address.region, 120).toLowerCase();
      const countryCode = textValue(address.country_code, 8).toLowerCase();
      const displayName = textValue(candidate && candidate.display_name, 400).toLowerCase();
      const stateMatches = stateAliases.some(function (alias) {
        return stateName === alias || displayName.includes(alias);
      });
      return stateMatches && (!countryCode || countryCode === "us");
    }) || null;
  }  async function locateCommunity() {
    const query = geocodeQuery();
    if (!hasPlaceSelection()) {
      setStatus("mapStatus", t("completePlace"), "warning");
      return;
    }
    setStatus("mapStatus", t("locateConsent"), "info");
    const cacheKey = query.toLowerCase().replace(/\s+/g, " ").trim();
    const cached = await dbGet(GEOCODE_STORE, cacheKey);
    let result = cached && cached.result;
    if (!result) {
      const elapsed = Date.now() - state.lastGeocodeAt;
      if (elapsed < 1000) await delay(1000 - elapsed);
      const url = new URL("https://nominatim.openstreetmap.org/search");
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("q", query);
      url.searchParams.set("countrycodes", geocodeCountryCode());
      url.searchParams.set("limit", "8");
      url.searchParams.set("addressdetails", "1");
      state.lastGeocodeAt = Date.now();
      const response = await fetch(url.toString(), {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("nominatim-" + response.status);
      const results = await response.json();
      if (!Array.isArray(results) || !results.length) throw new Error("nominatim-empty");
      const matched = matchingGeocodeResult(results);
      if (!matched) throw new Error("nominatim-state-mismatch");
      result = {
        latitude: Number(matched.lat),
        longitude: Number(matched.lon),
        displayName: textValue(matched.display_name, 400),
      };
      if (!Number.isFinite(result.latitude) || !Number.isFinite(result.longitude)) {
        throw new Error("nominatim-coordinates");
      }
      await dbPut(GEOCODE_STORE, {
        query: cacheKey,
        result: result,
        cachedAt: new Date().toISOString(),
      });
    }
    state.workspace.profile = sanitizeProfile(Object.assign({}, state.workspace.profile, result));
    await persistWorkspace();
    renderMap();
    renderCommunitySnapshot();
    setStatus("mapStatus", t("located"), "success");
  }

  function delay(milliseconds) {
    return new Promise(function (resolve) { window.setTimeout(resolve, milliseconds); });
  }

  function renderMap() {
    const root = byId("communityMap");
    if (!root) return;
    const profile = state.workspace.profile;
    const latitude = Number(profile.latitude);
    const longitude = Number(profile.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      root.setAttribute("aria-label", t("noProfile"));
      root.replaceChildren();
      const message = document.createElement("p");
      message.className = "map-placeholder";
      message.textContent = hasPlaceSelection() ? "Loading the selected community map..." : t("noProfile");
      root.appendChild(message);
      if (hasPlaceSelection()) {
        const searchUrl = new URL("https://www.openstreetmap.org/search");
        searchUrl.searchParams.set("query", geocodeQuery());
        const fallback = safeAnchor(searchUrl.href, "Open this place in OpenStreetMap");
        if (fallback) {
          fallback.className = "map-fallback-link";
          root.appendChild(fallback);
        }
      }
      return;
    }
    const place = textValue(profile.community || profile.name, 200) || t("community");
    root.setAttribute("aria-label", [place, latitude.toFixed(5), longitude.toFixed(5)].join(", "));
    root.replaceChildren();

    const latitudeSpan = 0.06;
    const longitudeSpan = 0.09;
    const bbox = [
      longitude - longitudeSpan,
      latitude - latitudeSpan,
      longitude + longitudeSpan,
      latitude + latitudeSpan,
    ].map(function (value) { return value.toFixed(6); }).join(",");
    const mapUrl = new URL("https://www.openstreetmap.org/export/embed.html");
    mapUrl.searchParams.set("bbox", bbox);
    mapUrl.searchParams.set("layer", "mapnik");
    mapUrl.searchParams.set("marker", latitude.toFixed(6) + "," + longitude.toFixed(6));

    const frame = document.createElement("iframe");
    frame.className = "osm-map-frame";
    frame.title = "Interactive OpenStreetMap of " + place;
    frame.loading = "eager";
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    frame.src = mapUrl.href;
    root.appendChild(frame);

    const attribution = safeAnchor("https://www.openstreetmap.org/copyright", t("osmAttribution"));
    if (attribution) {
      attribution.className = "map-attribution";
      root.appendChild(attribution);
    }
  }

  function safeHttpUrl(value) {
    try {
      if (typeof explorer().safeUrl === "function") {
        const checked = explorer().safeUrl(value);
        if (!checked) return "";
        value = checked;
      }
      const url = new URL(String(value), window.location.href);
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }

  function safeAnchor(url, label) {
    const checked = safeHttpUrl(url);
    if (!checked) return null;
    const anchor = document.createElement("a");
    anchor.href = checked;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.referrerPolicy = "no-referrer";
    anchor.textContent = label;
    return anchor;
  }

  function shareProfile() {
    const profile = state.workspace.profile;
    const output = {};
    ["geoid", "state", "stateCode", "county", "placeType"].forEach(function (field) {
      const value = textValue(profile[field], 120);
      if (value) output[field] = value;
    });
    if (Number.isFinite(profile.latitude)) output.latitude = Number(profile.latitude.toFixed(5));
    if (Number.isFinite(profile.longitude)) output.longitude = Number(profile.longitude.toFixed(5));
    return output;
  }

  function compactId(id) {
    const index = catalog().findIndex(function (item) { return itemId(item) === id; });
    return index >= 0 ? index.toString(36) : "";
  }

  function expandCompactId(token) {
    if (typeof token !== "string" || !/^[0-9a-z]+$/.test(token)) return "";
    const index = parseInt(token, 36);
    return catalog()[index] ? itemId(catalog()[index]) : "";
  }

  function encodeSharePayload(payload) {
    const bytes = new TextEncoder().encode(JSON.stringify(payload));
    let binary = "";
    bytes.forEach(function (byte) { binary += String.fromCharCode(byte); });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function decodeSharePayload(value) {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, function (character) { return character.charCodeAt(0); });
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function createShareLink() {
    const payload = {
      v: SCHEMA_VERSION,
      s: state.workspace.savedIds.map(compactId).filter(Boolean),
      c: state.workspace.compareIds.map(compactId).filter(Boolean),
      f: controlledFilters(),
      l: state.language,
      g: shareProfile(),
    };
    const url = new URL(window.location.href);
    url.hash = "s=" + encodeSharePayload(payload);
    if (url.href.length > MAX_SHARE_LENGTH) throw new Error("share-length");
    return url.href;
  }

  function validateSharePayload(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload) || payload.v !== SCHEMA_VERSION) {
      throw new Error("share-schema");
    }
    const savedTokens = Array.isArray(payload.s) ? payload.s.slice(0, MAX_IDS) : [];
    const compareTokens = Array.isArray(payload.c) ? payload.c.slice(0, MAX_COMPARE) : [];
    const savedIds = uniqueKnownIds(savedTokens.map(expandCompactId), MAX_IDS);
    const compareIds = uniqueKnownIds(compareTokens.map(expandCompactId), MAX_COMPARE)
      .filter(function (id) { return savedIds.includes(id); });
    const filters = payload.f && typeof payload.f === "object" && !Array.isArray(payload.f) ? payload.f : {};
    const language = ALLOWED_LANGUAGES.includes(payload.l) ? payload.l : "en";
    return {
      savedIds: savedIds,
      compareIds: compareIds,
      filters: filters,
      language: language,
      profile: sanitizeProfile(payload.g),
    };
  }

  async function importShareFromHash() {
    if (!window.location.hash.startsWith("#s=") || window.location.href.length > MAX_SHARE_LENGTH) return;
    try {
      const shared = validateSharePayload(decodeSharePayload(window.location.hash.slice(3)));
      state.workspace.savedIds = shared.savedIds;
      state.workspace.compareIds = shared.compareIds;
      state.workspace.profile = shared.profile;
      shared.savedIds.forEach(function (id) {
        if (!state.workspace.roadmapAssignments[id]) {
          state.workspace.roadmapAssignments[id] = inferPhase(catalogMap().get(id));
        }
      });
      state.language = shared.language;
      localStorage.setItem(LANGUAGE_KEY, state.language);
      applyControlledFilters(shared.filters);
      await persistWorkspace();
    } catch (error) {
      setStatus("shareStatus", t("invalidWorkspace"), "error");
      reportError(error);
    }
  }

  function showShareDialog() {
    const input = byId("shareLink");
    try {
      const link = createShareLink();
      if (input) {
        input.value = link;
        input.readOnly = true;
      }
      setStatus("shareStatus", t("shareReady") + " " + t("notesExcluded"), "success");
      openDialog("shareDialog");
    } catch (error) {
      setStatus("shareStatus", t("shareTooLong"), "warning");
      openDialog("shareDialog");
    }
  }

  async function copyShareLink() {
    const input = byId("shareLink");
    if (!input || !input.value) return;
    try {
      await navigator.clipboard.writeText(input.value);
      setStatus("shareStatus", t("copied"), "success");
    } catch (error) {
      input.focus();
      input.select();
      setStatus("shareStatus", t("copyFailed"), "warning");
    }
  }

  function exportWorkspace() {
    const payload = Object.assign({}, state.workspace, {
      schema: SCHEMA_VERSION,
      catalogVersion: catalogVersion(),
      exportedAt: new Date().toISOString(),
    });
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }),
      fileStem() + ".rerc-workspace"
    );
    setStatus("shareStatus", t("exported"), "success");
  }

  async function importWorkspace(file) {
    if (!file || file.size > MAX_FILE_BYTES) throw new Error("workspace-size");
    const text = await file.text();
    if (new Blob([text]).size > MAX_FILE_BYTES) throw new Error("workspace-size");
    const parsed = JSON.parse(text);
    state.workspace = sanitizeWorkspace(parsed, true);
    state.workspace.id = DEFAULT_WORKSPACE_ID;
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    await persistWorkspace();
    hydrateInputs();
    refreshWorkspaceUI();
    setStatus("shareStatus", t("imported"), "success");
  }

  function projectExportModel(includeNotes) {
    const items = savedItems().map(function (item) {
      const evidence = evidenceFor(item);
      const deadline = reviewedDeadline(item);
      return {
        item: item,
        phase: state.workspace.roadmapAssignments[itemId(item)] || inferPhase(item),
        reasons: evidence.reasons,
        cautions: evidence.cautions,
        deadline: deadline,
      };
    });
    return {
      schema: SCHEMA_VERSION,
      title: state.workspace.projectTitle || t("projectWorkspace"),
      notes: includeNotes ? state.workspace.projectNotes : "",
      profile: state.workspace.profile,
      items: items,
      generatedAt: new Date().toISOString(),
      catalogVersion: catalogVersion(),
    };
  }

  function catalogVersion() {
    return textValue(window.RERC_CATALOG_VERSION, 80) ||
      String(catalog().length) + "-" + textValue(window.RERC_CATALOG && window.RERC_CATALOG.updated, 20);
  }

  function csvCell(value) {
    let text = value == null ? "" : String(value).replace(/\r?\n/g, " ").trim();
    if (/^[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  }

  function exportPlanCsv() {
    const model = projectExportModel(true);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    const headers = [
      "Project title",
      "Community",
      "State or territory",
      "Profile source",
      "Profile vintage",
      "Item ID",
      "Type",
      "Title",
      "Organization",
      "Roadmap phase",
      "Status",
      "Eligible applicants",
      "Geography",
      "Project stage",
      "Amount or cost",
      "Match or cost share",
      "Reviewed deadline",
      "Why it matches",
      "Cautions",
      "Summary",
      "Official source",
      "Project notes",
    ];
    const rows = [headers.map(csvCell).join(",")];
    model.items.forEach(function (entry) {
      const item = entry.item;
      rows.push([
        model.title,
        model.profile.community || model.profile.name || "",
        model.profile.state || "",
        model.profile.source || "",
        model.profile.vintage || "",
        itemId(item),
        item.item_type,
        item.title,
        item.organization,
        entry.phase,
        item.status,
        item.eligible_users,
        item.geography,
        item.project_stage,
        item.amount_or_cost,
        item.match_or_cost,
        entry.deadline ? isoDate(entry.deadline.date) : "",
        entry.reasons.join(" "),
        entry.cautions.join(" "),
        summaryFor(item),
        safeHttpUrl(item.source_url),
        model.notes,
      ].map(csvCell).join(","));
    });
    downloadBlob(
      new Blob(["\ufeff" + rows.join("\r\n")], { type: "text/csv;charset=utf-8" }),
      fileStem() + ".csv"
    );
    setStatus("shareStatus", t("csvExported"), "success");
  }

  function xmlEscape(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function docxParagraph(text, style, relationshipId) {
    const styleXml = style ? '<w:pPr><w:pStyle w:val="' + xmlEscape(style) + '"/></w:pPr>' : "";
    const run = '<w:r><w:t xml:space="preserve">' + xmlEscape(text) + "</w:t></w:r>";
    const content = relationshipId
      ? '<w:hyperlink r:id="' + relationshipId + '" w:history="1"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr><w:t>' +
        xmlEscape(text) + "</w:t></w:r></w:hyperlink>"
      : run;
    return "<w:p>" + styleXml + content + "</w:p>";
  }

  async function exportPlanDocx() {
    const model = projectExportModel(true);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    if (!window.JSZip) throw new Error("jszip-unavailable");
    const relationships = [];
    const body = [];
    body.push(docxParagraph(model.title, "Title"));
    body.push(docxParagraph(t("communitySnapshot"), "Heading1"));
    profileRows(model.profile).forEach(function (row) {
      body.push(docxParagraph(row.label + ": " + row.value));
    });
    if (model.notes) {
      body.push(docxParagraph("Project notes", "Heading1"));
      model.notes.split(/\r?\n/).forEach(function (line) { body.push(docxParagraph(line || " ")); });
    }
    body.push(docxParagraph(t("roadmap"), "Heading1"));
    PHASES.forEach(function (phase) {
      const entries = model.items.filter(function (entry) { return entry.phase === phase; });
      if (!entries.length) return;
      body.push(docxParagraph(t(phase.toLowerCase()), "Heading2"));
      entries.forEach(function (entry) {
        const item = entry.item;
        body.push(docxParagraph(textValue(item.title, 500), "Heading3"));
        [
          [t("organization"), item.organization],
          [t("type"), item.item_type],
          [t("status"), item.status],
          [t("applicant"), item.eligible_users],
          [t("geography"), item.geography],
          [t("stage"), item.project_stage],
          [t("amount"), item.amount_or_cost],
          [t("match"), item.match_or_cost],
          [t("deadline"), item.deadline_or_availability],
          [t("whyMatch"), entry.reasons.join(" ")],
          [t("cautions"), entry.cautions.join(" ")],
        ].forEach(function (row) {
          if (row[1]) body.push(docxParagraph(row[0] + ": " + row[1]));
        });
        body.push(docxParagraph(summaryFor(item)));
        const source = safeHttpUrl(item.source_url);
        if (source) {
          const relationshipId = "rId" + (relationships.length + 1);
          relationships.push({ id: relationshipId, url: source });
          body.push(docxParagraph(t("openSource"), "", relationshipId));
        }
      });
    });
    body.push(docxParagraph(t("officialEnglish")));

    const documentXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
      "<w:body>" + body.join("") +
      '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" ' +
      'w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>' +
      "</w:body></w:document>";
    const relsXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
      relationships.map(function (relationship) {
        return '<Relationship Id="' + relationship.id +
          '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" ' +
          'Target="' + xmlEscape(relationship.url) + '" TargetMode="External"/>';
      }).join("") + "</Relationships>";
    const stylesXml =
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
      '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>' +
      '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>' +
      '<w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>' +
      '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>' +
      '<w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style></w:styles>';
    const zip = new window.JSZip();
    zip.file("[Content_Types].xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
      '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
      '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
      "</Types>");
    zip.folder("_rels").file(".rels",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
      '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
      '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>' +
      "</Relationships>");
    zip.folder("word").file("document.xml", documentXml);
    zip.folder("word").file("styles.xml", stylesXml);
    zip.folder("word").folder("_rels").file("document.xml.rels", relsXml);
    zip.folder("docProps").file("core.xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
      'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>' + xmlEscape(model.title) +
      '</dc:title><dc:creator>RERC Community Explorer</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">' +
      new Date().toISOString() + "</dcterms:created></cp:coreProperties>");
    zip.folder("docProps").file("app.xml",
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" ' +
      'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
      "<Application>RERC Community Explorer</Application></Properties>");
    const blob = await zip.generateAsync({
      type: "blob",
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      compression: "DEFLATE",
    });
    downloadBlob(blob, fileStem() + ".docx");
    setStatus("shareStatus", t("docxExported"), "success");
  }

  function exportCalendar() {
    const entries = deadlineItems().filter(function (entry) {
      return entry.deadline.date.getTime() >= new Date().setHours(0, 0, 0, 0);
    });
    if (!entries.length) {
      setStatus("shareStatus", t("noDeadlines"), "warning");
      return;
    }
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RERC Community Explorer//EN", "CALSCALE:GREGORIAN"];
    entries.forEach(function (entry, index) {
      const date = isoDate(entry.deadline.date).replace(/-/g, "");
      const next = new Date(entry.deadline.date);
      next.setDate(next.getDate() + 1);
      lines.push(
        "BEGIN:VEVENT",
        "UID:" + icsEscape(itemId(entry.item) + "-" + date + "@rerc-community-explorer"),
        "DTSTAMP:" + stamp,
        "DTSTART;VALUE=DATE:" + date,
        "DTEND;VALUE=DATE:" + isoDate(next).replace(/-/g, ""),
        "SUMMARY:" + icsEscape(textValue(entry.item.title, 500) + " deadline"),
        "DESCRIPTION:" + icsEscape(
          [summaryFor(entry.item), safeHttpUrl(entry.item.source_url)].filter(Boolean).join("\n")
        ),
        "URL:" + icsEscape(safeHttpUrl(entry.item.source_url)),
        "END:VEVENT"
      );
    });
    lines.push("END:VCALENDAR");
    downloadBlob(
      new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" }),
      fileStem() + "-deadlines.ics"
    );
    setStatus("shareStatus", t("calendarExported"), "success");
  }

  function icsEscape(value) {
    return String(value || "")
      .replace(/\\/g, "\\\\")
      .replace(/\r?\n/g, "\\n")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;");
  }

  function isoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function fileStem() {
    const base = textValue(state.workspace.projectTitle, 120) ||
      textValue(state.workspace.profile.community || state.workspace.profile.name, 120) ||
      "RERC-Community-Plan";
    return base.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "RERC-Community-Plan";
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.hidden = true;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function exportRercie() {
    const includeNotes = !state.workspace.projectNotes ||
      window.confirm(t("includeNotes"));
    const model = projectExportModel(includeNotes);
    if (!model.items.length) {
      setStatus("shareStatus", t("noExportItems"), "warning");
      return;
    }
    const payload = {
      schema: "rercie-handoff",
      version: 1,
      generatedAt: model.generatedAt,
      catalogVersion: model.catalogVersion,
      communityProfile: model.profile,
      projectTitle: includeNotes ? model.title : "",
      projectNotes: includeNotes ? model.notes : "",
      roadmap: PHASES.map(function (phase) {
        return {
          phase: phase,
          itemIds: model.items.filter(function (entry) { return entry.phase === phase; })
            .map(function (entry) { return itemId(entry.item); }),
        };
      }),
      selectedRecords: model.items.map(function (entry) {
        const item = entry.item;
        return {
          item_id: itemId(item),
          item_type: textValue(item.item_type, 80),
          title: textValue(item.title, 500),
          organization: textValue(item.organization, 300),
          status: textValue(item.status, 120),
          geography: textValue(item.geography, 300),
          eligible_users: textValue(item.eligible_users, 2000),
          project_stage: textValue(item.project_stage, 300),
          amount_or_cost: textValue(item.amount_or_cost, 500),
          match_or_cost: textValue(item.match_or_cost, 500),
          deadline_or_availability: textValue(item.deadline_or_availability, 1000),
          summary: summaryFor(item),
          whyMatch: entry.reasons,
          cautions: entry.cautions,
          roadmapPhase: entry.phase,
          source_url: safeHttpUrl(item.source_url),
        };
      }),
      installerUrl: INSTALLER_URL,
      boundary:
        "This handoff file contains only user-approved local notes and public catalog data. It is a local file export; RERC-e processes it locally only after you open or import it. It does not contain an API key or session token.",
    };
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }),
      fileStem() + ".rercie"
    );
    const status = byId("shareStatus");
    if (status) {
      status.replaceChildren();
      status.dataset.status = "success";
      status.appendChild(document.createTextNode(t("rercieExported") + " "));
      const installer = safeAnchor(INSTALLER_URL, t("installerFallback"));
      if (installer) status.appendChild(installer);
    }
  }

  async function deleteLocalData() {
    await Promise.all([dbClear(WORKSPACE_STORE), dbClear(GEOCODE_STORE)]);
    localStorage.removeItem(LANGUAGE_KEY);
    localStorage.removeItem(LAST_WORKSPACE_KEY);
    state.language = "en";
    state.workspace = defaultWorkspace(DEFAULT_WORKSPACE_ID);
    state.savedOnly = false;
    hydrateInputs();
    applyLanguage();
    refreshWorkspaceUI();
    setStatus("shareStatus", t("deleted"), "success");
  }

  function applyLanguage() {
    document.documentElement.lang = state.language;
    const labels = {
      showSavedOnly: state.savedOnly ? "allMatches" : "savedOnly",
      openCompare: "compare",
      exportCalendar: "deadlines",
      exportPlanWord: "projectWorkspace",
      exportPlanCsv: "projectWorkspace",
      exportWorkspaceFile: "exported",
      exportRercie: "rercieExported",
      openLanguage: "language",
    };
    Object.keys(labels).forEach(function (id) {
      const element = byId(id);
      if (element && element.tagName === "BUTTON") element.setAttribute("aria-label", t(labels[id]));
    });
    const languageButton = byId("openLanguage");
    const languageLabel = languageButton && languageButton.querySelector("span");
    if (languageLabel) languageLabel.textContent = state.language === "es" ? t("spanish") : t("english");
    const mobileNav = byId("plannerMobileNav");
    if (mobileNav) {
      mobileNav.setAttribute("aria-label", t("projectWorkspace"));
      mobileNav.querySelectorAll("[data-label-key]").forEach(function (item) {
        const label = item.querySelector("span:not(.mobile-nav-badge)");
        if (label) label.textContent = t(item.dataset.labelKey);
      });
    }
    ["applicantOptions", "topicOptions"].forEach(function (rootId) {
      const root = byId(rootId);
      if (!root || root.dataset.choicePagerReady !== "true") return;
      const controls = root.nextElementSibling;
      if (!controls || !controls.classList.contains("choice-pager-controls")) return;
      const buttons = controls.querySelectorAll("button");
      if (buttons[0]) buttons[0].textContent = t("back");
      if (buttons[1]) buttons[1].textContent = t("next");
      const choices = choiceItems(root);
      const current = Number(root.dataset.choicePage || 0);
      const start = current * 6;
      const status = controls.querySelector(".choice-pager-status");
      if (status) status.textContent = t("choicesPage", {
        label: t(root.dataset.choiceLabelKey),
        start: start + 1,
        end: Math.min(start + 6, choices.length),
        total: choices.length,
      });
    });
    const dialog = byId("languageDialog");
    if (dialog) {
      dialog.querySelectorAll("[data-language]").forEach(function (button) {
        const language = button.dataset.language;
        if (button instanceof HTMLInputElement) button.checked = language === state.language;
        else button.setAttribute("aria-pressed", language === state.language ? "true" : "false");
      });
    }
    renderProfileSummary();
    refreshWorkspaceUI();
    if (window.RERCI18N) window.RERCI18N.setLanguage(state.language);
  }

  async function setLanguage(language) {
    if (!ALLOWED_LANGUAGES.includes(language)) return;
    state.language = language;
    localStorage.setItem(LANGUAGE_KEY, language);
    applyLanguage();
    closeDialog(byId("languageDialog"));
  }

  function hydrateInputs() {
    const title = byId("projectTitle");
    const notes = byId("projectNotes");
    if (title) title.value = state.workspace.projectTitle;
    if (notes) {
      notes.value = state.workspace.projectNotes;
      notes.maxLength = MAX_NOTES;
    }
    if (typeof explorer().setCommunitySelection === "function" && state.workspace.profile.stateCode) {
      explorer().setCommunitySelection(
        state.workspace.profile.stateCode,
        state.workspace.profile.placeType,
        state.workspace.profile.geoid
      );
    }
    renderProfileSummary();
  }

  function setupEventHandlers() {
    document.addEventListener("click", function (event) {
      const languageOpener = event.target.closest("#openLanguage");
      if (languageOpener) {
        event.preventDefault();
        openDialog("languageDialog");
        return;
      }
      const communityEntry = event.target.closest("[data-community-entry]");
      if (communityEntry) {
        event.preventDefault();
        revealCommunityForm(true);
        return;
      }
      const action = event.target.closest("[data-action]");
      if (action && action.dataset.itemId) {
        if (action.dataset.action === "planner-save") {
          event.preventDefault();
          toggleSaved(action.dataset.itemId).catch(reportError);
          return;
        }
        if (action.dataset.action === "planner-compare") {
          event.preventDefault();
          toggleCompare(action.dataset.itemId).catch(reportError);
          return;
        }
      }

      const close = event.target.closest("[data-dialog-close]");
      if (close) closeDialog(close.closest("dialog, [role='dialog']"));
      const language = event.target.closest("[data-language]");
      if (language) setLanguage(language.dataset.language).catch(reportError);
    });

    const results = (explorer().elements && explorer().elements.results) || byId("results");
    if (results && window.MutationObserver) {
      state.observer = new MutationObserver(function () {
        window.requestAnimationFrame(decorateResults);
      });
      state.observer.observe(results, { childList: true, subtree: true });
    }

    bind("showSavedOnly", "click", function (event) {
      toggleSavedOnly(event.currentTarget.type === "checkbox" ? event.currentTarget.checked : undefined);
    });
    bind("openCompare", "click", function () { renderComparison(); openDialog("compareDialog"); });
    bind("compareSaved", "click", function () { renderComparison(); openDialog("compareDialog"); });
    bind("toggleSavedTray", "click", function (event) {
      const tray = byId("savedTray");
      if (!tray) return;
      const expanded = event.currentTarget.getAttribute("aria-expanded") === "true";
      event.currentTarget.setAttribute("aria-expanded", expanded ? "false" : "true");
      tray.hidden = expanded;
      if (!expanded) {
        const focusable = tray.querySelector("button, a, select");
        if (focusable) focusable.focus();
      }
    });
    bind("loadCommunityProfile", "click", function () { loadProjectedProfile().catch(reportError); });
    bind("refreshProfile", "click", function () { loadProjectedProfile().catch(reportError); });
    bind("locateCommunity", "click", function () {
      locateCommunity().catch(function (error) {
        setStatus("mapStatus", t("locateFailed"), "error");
        reportError(error);
      });
    });
    bind("exportCalendar", "click", exportCalendar);
    bind("exportPlanWord", "click", function () { exportPlanDocx().catch(reportError); });
    bind("exportPlanCsv", "click", exportPlanCsv);
    bind("exportWorkspaceFile", "click", exportWorkspace);
    bind("exportRercie", "click", exportRercie);
    bind("deleteLocalData", "click", function () { deleteLocalData().catch(reportError); });
    bind("shareWorkspace", "click", showShareDialog);
    bind("copyShareLink", "click", function () { copyShareLink().catch(reportError); });


    const importInput = byId("importWorkspaceFile");
    if (importInput) {
      importInput.accept = ".rerc-workspace,application/json";
      importInput.addEventListener("change", function () {
        const file = importInput.files && importInput.files[0];
        importWorkspace(file).catch(function (error) {
          setStatus("shareStatus", t("invalidWorkspace"), "error");
          reportError(error);
        }).finally(function () { importInput.value = ""; });
      });
    }

    const title = byId("projectTitle");
    if (title) {
      title.maxLength = 200;
      title.addEventListener("input", function () {
        state.workspace.projectTitle = title.value.slice(0, 200);
        schedulePersist();
      });
    }
    const notes = byId("projectNotes");
    if (notes) {
      notes.maxLength = MAX_NOTES;
      notes.addEventListener("input", function () {
        state.workspace.projectNotes = notes.value.slice(0, MAX_NOTES);
        schedulePersist();
      });
    }
    const communityName = byId("communityName");
    const communityState = byId("stateSelect");
    const communityType = byId("placeTypeSelect");
    [communityState, communityType, communityName].forEach(function (control) {
      if (!control) return;
      control.addEventListener("change", function () {
        control.setCustomValidity("");
        control.removeAttribute("aria-invalid");
        syncCommunityGate();
      });
    });

    const filters = byId("communityFilters");
    if (filters) {
      filters.addEventListener("change", function (event) {
        captureProfileFromFilters();
        renderProfileSummary();
        syncCommunityGate();
        if (event.target && event.target.id === "communityName" && event.target.value) {
          loadProjectedProfile().catch(reportError);
        }
      });
    }
    const roadmap = byId("roadmap");
    if (roadmap) {
      roadmap.addEventListener("change", function (event) {
        const select = event.target.closest("[data-roadmap-id]");
        if (!select || !PHASES.includes(select.value)) return;
        state.workspace.roadmapAssignments[select.dataset.roadmapId] = select.value;
        persistWorkspace().then(refreshWorkspaceUI).catch(reportError);
      });
    }
  }

  function bind(id, eventName, handler) {
    const element = byId(id);
    if (element) element.addEventListener(eventName, handler);
  }

  async function initialize() {
    state.language = ALLOWED_LANGUAGES.includes(localStorage.getItem(LANGUAGE_KEY))
      ? localStorage.getItem(LANGUAGE_KEY)
      : "en";
    state.db = await openDatabase();
    const workspaceId = textValue(localStorage.getItem(LAST_WORKSPACE_KEY), 80) || DEFAULT_WORKSPACE_ID;
    const stored = await dbGet(WORKSPACE_STORE, workspaceId);
    try {
      state.workspace = stored ? sanitizeWorkspace(stored, false) : defaultWorkspace(workspaceId);
    } catch (error) {
      reportError(error);
      state.workspace = defaultWorkspace(workspaceId);
    }
    localStorage.setItem(LAST_WORKSPACE_KEY, state.workspace.id);
    await importShareFromHash();
    hydrateInputs();
    setupWizard();
    setupChoicePager("applicantOptions", "applicantChoices");
    setupChoicePager("topicOptions", "topicChoices");
    setupMobileNavigation();
    setupEventHandlers();
    applyLanguage();
    refreshWorkspaceUI();
    renderMap();
    if (hasPlaceSelection() && (!Number.isFinite(state.workspace.profile.latitude) || !Number.isFinite(state.workspace.profile.longitude))) {
      try {
        await locateCommunity();
      } catch (error) {
        setStatus("mapStatus", t("locateFailed"), "warning");
        reportError(error);
      }
    } else {
      setStatus("mapStatus", hasPlaceSelection() ? t("located") : t("locateConsent"), "info");
    }
    document.documentElement.classList.add("rerc-planner-ready");
    document.dispatchEvent(new CustomEvent("rerc:planner-ready", {
      detail: { schema: SCHEMA_VERSION, workspaceId: state.workspace.id },
    }));
  }

  function start() {
    if (!window.RERCExplorer) {
      window.setTimeout(start, 25);
      return;
    }
    initialize().catch(function (error) {
      reportError(error);
      document.documentElement.classList.add("rerc-planner-error");
      setStatus("shareStatus", "The local planner could not start in this browser.", "error");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
