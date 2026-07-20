(function () {
  "use strict";

  const LANGUAGE_KEY = "rerc.language";
  const originalText = new WeakMap();
  const originalAttributes = new WeakMap();
  let language = "en";
  let observer = null;

  const ES = {
    "Skip to the community explorer": "Saltar al explorador comunitario",
    "Community Explorer": "Explorador comunitario",
    "Independent community-built tool": "Herramienta independiente creada por la comunidad",
    "Full catalog": "Catálogo completo",
    "English": "Inglés",
    "Start with your place": "Empiece con su comunidad",
    "Turn a community goal into a practical plan.": "Convierta una meta comunitaria en un plan práctico.",
    "Find funding, hands-on help, and examples from communities like yours. Save the best matches and take your plan with you.": "Encuentre financiamiento, ayuda práctica y ejemplos de comunidades como la suya. Guarde las mejores opciones y llévese su plan.",
    "Build your community profile": "Crear el perfil de su comunidad",
    "Funding": "Financiamiento",
    "Resources": "Recursos",
    "Case studies": "Casos prácticos",
    "Outdoor recreation photo:": "Foto de recreación al aire libre:",
    "Community": "Comunidad",
    "Tell us about your place": "Cuéntenos sobre su comunidad",
    "Priorities": "Prioridades",
    "Choose your goals": "Elija sus metas",
    "Matches": "Opciones",
    "Review what fits": "Revise sus opciones",
    "Plan": "Plan",
    "Save your next steps": "Guarde sus próximos pasos",
    "Hide community questions": "Ocultar preguntas de la comunidad",
    "Show community questions": "Mostrar preguntas de la comunidad",
    "Community profile": "Perfil comunitario",
    "First, tell us about your community.": "Primero, cuéntenos sobre su comunidad.",
    "A few answers help us find stronger matches. They do not decide whether you are eligible.": "Unas pocas respuestas nos ayudan a encontrar mejores opciones. No determinan si usted cumple los requisitos.",
    "Your place": "Su comunidad",
    "Choose a state, a place type, and then your community.": "Elija un estado, un tipo de lugar y luego su comunidad.",
    "Place type": "Tipo de lugar",
    "Choose a state first": "Primero elija un estado",
    "County, town, city, or Census place": "Condado, pueblo, ciudad o lugar del Censo",
    "Choose a place type first": "Primero elija un tipo de lugar",
    "State or territory, place type, and community are required before you continue.": "Debe elegir el estado o territorio, el tipo de lugar y la comunidad antes de continuar.",
    "Includes every county or county equivalent and every Census place in the 50 states, D.C., and U.S. territories.": "Incluye todos los condados o equivalentes y todos los lugares del Censo en los 50 estados, D.C. y los territorios de EE. UU.",
    "Load community profile": "Cargar perfil comunitario",
    "Choose a state or territory first.": "Primero elija un estado o territorio.",
    "Choose a place type": "Elija un tipo de lugar",
    "Choose a county or a town, city, or Census place.": "Elija un condado o un pueblo, ciudad o lugar del Censo.",
    "Choose a community.": "Elija una comunidad.",
    "Community selected. Loading public profile and map...": "Comunidad seleccionada. Cargando el perfil público y el mapa...",
    "No matching Census places were found.": "No se encontraron lugares del Censo que coincidan.",
    "Enter a community and choose its location.": "Escriba una comunidad y elija su ubicación.",
    "Community name": "Nombre de la comunidad",
    "State, D.C., or U.S. territory": "Estado, D.C. o territorio de EE. UU.",
    "Community type": "Tipo de comunidad",
    "Any community type": "Cualquier tipo de comunidad",
    "Town or city": "Pueblo o ciudad",
    "County or region": "Condado o región",
    "Tribal community": "Comunidad tribal",
    "Statewide or multi-community": "Estatal o varias comunidades",
    "Community name and state or territory are required before you continue.": "Debe escribir la comunidad y elegir el estado o territorio antes de continuar.",
    "Look up community": "Buscar comunidad",
    "Enter a place to add public community facts.": "Escriba un lugar para agregar datos públicos de la comunidad.",
    "Community snapshot": "Resumen de la comunidad",
    "What we found": "Lo que encontramos",
    "Refresh": "Actualizar",
    "Your priorities": "Sus prioridades",
    "Choose what you want to do and who will lead it.": "Elija lo que quiere hacer y quién dirigirá el trabajo.",
    "Search words or project name": "Palabras de búsqueda o nombre del proyecto",
    "Who will lead the work?": "¿Quién dirigirá el trabajo?",
    "What are you working on?": "¿En qué está trabajando?",
    "What step are you on?": "¿En qué etapa está?",
    "Plan for later rounds": "Planificar para futuras convocatorias",
    "Include closed opportunities.": "Incluir oportunidades cerradas.",
    "Reset answers": "Borrar respuestas",
    "Your matches": "Sus opciones",
    "Funding, resources, and case studies for rural communities": "Financiamiento, recursos y casos prácticos para comunidades rurales",
    "Choose a place and answer the questions. Your list will update as you go.": "Elija un lugar y responda las preguntas. La lista se actualizará mientras avanza.",
    "Saved": "Guardados",
    "Compare": "Comparar",
    "All": "Todos",
    "All matches": "Todas las opciones",
    "Next submission deadline": "Próxima fecha límite",
    "Checking dated funding matches...": "Buscando fechas de financiamiento...",
    "View program": "Ver programa",
    "Funding view": "Vista de financiamiento",
    "Choose funding view": "Elegir vista de financiamiento",
    "List": "Lista",
    "Funding deadlines": "Fechas límite de financiamiento",
    "Upcoming application calendar": "Calendario de próximas solicitudes",
    "Change calendar month": "Cambiar mes del calendario",
    "Previous month": "Mes anterior",
    "Next month": "Mes siguiente",
    "Today": "Hoy",
    "Scrollable funding deadline calendar": "Calendario desplazable de fechas límite de financiamiento",
    "Funding deadline calendar": "Calendario de fechas límite de financiamiento",
    "Dated deadline": "Fecha límite con día",
    "Rolling / ongoing": "Continuo / sin fecha fija",
    "Recurring cycle / next date pending": "Ciclo recurrente / próxima fecha pendiente",
    "Closed / next cycle pending": "Cerrado / próximo ciclo pendiente",
    "Deadlines vary by program": "Las fechas varían según el programa",
    "Active program period": "Período activo del programa",
    "Next deadline not announced": "Próxima fecha no anunciada",
    "Application timing": "Plazo de solicitud",
    "Application timing:": "Plazo de solicitud:",
    "Availability": "Disponibilidad",
    "Availability:": "Disponibilidad:",
    "Check current availability": "Confirme la disponibilidad actual",
    "Check the official program page.": "Revise la página oficial del programa.",
    "Last checked": "Última revisión",
    "Last checked:": "Última revisión:",
    "No upcoming dated funding deadline found.": "No hay una próxima fecha anunciada.",
    "Use the official program links to confirm current timing.": "Confirme las fechas en los enlaces oficiales.",
    "Next upcoming deadlines": "Próximas fechas límite",
    "No dated funding deadlines are available in these matches.": "Estas opciones no tienen fechas límite de financiamiento disponibles.",
    "Loading the selected community map...": "Cargando el mapa de la comunidad seleccionada...",
    "Open this place in OpenStreetMap": "Abrir este lugar en OpenStreetMap",
    "Sort": "Ordenar",
    "Most relevant": "Más relevante",
    "Name": "Nombre",
    "Status": "Estado",
    "Type": "Tipo",
    "Show": "Mostrar",
    "Your plan": "Su plan",
    "Build the next steps.": "Prepare los próximos pasos.",
    "Add a community to see a quick public profile.": "Agregue una comunidad para ver un breve perfil público.",
    "Community map": "Mapa de la comunidad",
    "Waiting for a place": "Esperando una ubicación",
    "Project roadmap": "Plan de trabajo del proyecto",
    "Save matches to build a roadmap.": "Guarde opciones para crear una ruta del proyecto.",
    "Deadlines": "Fechas límite",
    "Calendar": "Calendario",
    "Reviewed dates from saved funding will appear here.": "Aquí aparecerán las fechas revisadas del financiamiento guardado.",
    "Project details": "Detalles del proyecto",
    "Project title": "Título del proyecto",
    "Notes": "Notas",
    "Take your plan with you": "Llévese su plan",
    "Word plan": "Plan en Word",
    "CSV list": "Lista CSV",
    "Save workspace": "Guardar espacio de trabajo",
    "Open workspace": "Abrir espacio de trabajo",
    "Open in RERC-e": "Abrir en RERC-e",
    "Delete my saved data": "Borrar mis datos guardados",
    "Saved shortlist": "Lista guardada",
    "Your selected matches": "Sus opciones seleccionadas",
    "Use Save on any result to add it here.": "Use Guardar en cualquier resultado para agregarlo aquí.",
    "Compare selected": "Comparar seleccionados",
    "Full collection": "Colección completa",
    "Download every catalog record.": "Descargue todo el catálogo.",
    "These files include all funding opportunities, resources, and community examples with official links.": "Estos archivos incluyen todas las oportunidades de financiamiento, recursos y ejemplos comunitarios con enlaces oficiales.",
    "Word appendix": "Apéndice en Word",
    "Excel workbook": "Libro de Excel",
    "CSV file": "Archivo CSV",
    "Optional Windows tool": "Herramienta opcional para Windows",
    "Meet RERC-e, your local grant-writing guide.": "Conozca a RERC-e, su guía local para redactar subvenciones.",
    "RERC-e helps you review likely matches and start a grant draft with your own notes.": "RERC-e le ayuda a revisar opciones y comenzar un borrador de subvención con sus propias notas.",
    "The setup guide explains each step. You do not need an account, command line, or AI key to write on your computer. RERC-e checks its public community file first. If your community is not there, you can add a free Census API key and ask RERC-e to check Census.": "La guía explica cada paso. No necesita una cuenta, una línea de comandos ni una clave de IA para escribir en su computadora. RERC-e revisa primero su archivo público de comunidades. Si su comunidad no está allí, puede agregar una clave gratuita del Censo y pedir que RERC-e consulte el Censo.",
    "RERC-e is a community-built companion published by Timberwing Systems, an EPR, P.C. initiative. It is not an EPA grant program, does not determine eligibility, and does not submit applications.": "RERC-e es una herramienta comunitaria publicada por Timberwing Systems, una iniciativa de EPR, P.C. No es un programa de subvenciones de la EPA, no determina elegibilidad ni presenta solicitudes.",
    "The first time you use RERC-e, it downloads Google Gemma (about 0.81 GB). Before you apply, verify dates and rules on the official funding page.": "La primera vez que use RERC-e, descargará Google Gemma (aproximadamente 0.81 GB). Antes de solicitar, confirme las fechas y reglas en la página oficial del programa.",
    "Download RERC-e": "Descargar RERC-e",
    "Windows 10 or 11, 64-bit. No command line.": "Windows 10 u 11, 64 bits. Sin línea de comandos.",
    "Download the latest public RERC-e installer. It is not code-signed. Windows may warn that the publisher is unknown.": "Descargue el instalador público más reciente de RERC-e. No tiene firma de código. Windows puede avisar que el editor es desconocido.",
    "Read the Timberwing Systems license": "Leer la licencia de Timberwing Systems",
    "Review the source": "Revisar el código fuente",
    "This community-built explorer is not an EPA grant program. Program rules and dates can change. Check the funder's page before you apply or make a decision.": "Este explorador comunitario no es un programa de subvenciones de la EPA. Las reglas y fechas pueden cambiar. Revise la página del financiador antes de solicitar o tomar una decisión.",
    "Learn about RERC at EPA.gov": "Conocer RERC en EPA.gov",
    "Side-by-side review": "Comparación lado a lado",
    "Compare saved matches": "Comparar opciones guardadas",
    "Choose up to three saved items to compare.": "Elija hasta tres elementos guardados para comparar.",
    "Close": "Cerrar",
    "Share": "Compartir",
    "Share this workspace": "Compartir este espacio de trabajo",
    "Shared links include your community, filters, and selected records. Private notes are not included.": "Los enlaces compartidos incluyen la comunidad, los filtros y los registros seleccionados. No incluyen notas privadas.",
    "Share link": "Enlace para compartir",
    "Copy link": "Copiar enlace",
    "Language": "Idioma",
    "Choose a language": "Elegir un idioma",
    "Available languages": "Idiomas disponibles",
    "Current language": "Idioma actual",
    "Spanish interface": "Interfaz en español",
    "Program rules remain in their source language unless a reviewed translation is available.": "Las reglas de los programas permanecen en el idioma de la fuente, salvo que exista una traducción revisada.",
    "Done": "Listo",
    "Local government": "Gobierno local",
    "Tribe or Native community": "Tribu o comunidad indígena",
    "Nonprofit or community group": "Organización sin fines de lucro o grupo comunitario",
    "State agency": "Agencia estatal",
    "Business or tourism group": "Empresa o grupo de turismo",
    "School, library, or museum": "Escuela, biblioteca o museo",
    "Utility or public authority": "Empresa de servicios o autoridad pública",
    "Landowner or individual": "Propietario o persona",
    "Other or varies by program": "Otro o varía según el programa",
    "Parks, trails, and outdoor access": "Parques, senderos y acceso al aire libre",
    "Downtown and Main Street": "Centro y calle principal",
    "Tourism and visitor economy": "Turismo y economía de visitantes",
    "Business and jobs": "Empresas y empleos",
    "Transportation and safe access": "Transporte y acceso seguro",
    "Water and resilience": "Agua y resiliencia",
    "Conservation and public lands": "Conservación y tierras públicas",
    "History, arts, and culture": "Historia, arte y cultura",
    "Community services": "Servicios comunitarios",
    "Energy, climate, and cleanup": "Energía, clima y limpieza",
    "Planning and local capacity": "Planificación y capacidad local",
    "Any step": "Cualquier etapa",
    "Planning": "Planificación",
    "Early Design": "Diseño inicial",
    "Engineering": "Ingeniería",
    "Construction": "Construcción",
    "Implementation": "Implementación",
    "Operations/Maintenance": "Operaciones y mantenimiento",
    "Capacity Building": "Fortalecimiento de capacidades",
    "Acquisition": "Adquisición",
    "Cleanup": "Limpieza",
    "Save": "Guardar",
    "Remove": "Quitar",
    "Planning actions": "Acciones de planificación",
    "Case study": "Caso práctico",
    "Why it fits and details": "Por qué encaja y detalles",
    "Why it fits:": "Por qué encaja:",
    "Check:": "Revise:",
    "Topics:": "Temas:",
    "Where:": "Dónde:",
    "Who:": "Quién:",
    "Timing or amount:": "Fecha o monto:",
    "Checked:": "Revisado:",
    "Read the example": "Leer el ejemplo",
    "Open the resource": "Abrir el recurso",
    "View program details": "Ver detalles del programa",
    "Source link unavailable": "Enlace de la fuente no disponible",
    "match level": "nivel de coincidencia",
    "add details to rank": "agregue datos para ordenar las opciones",
    "Ways to pay for the work": "Formas de pagar el trabajo",
    "Grants, loans, tax credits, and other funding options.": "Subvenciones, préstamos, créditos fiscales y otras opciones de financiamiento.",
    "Tools and technical help": "Herramientas y ayuda técnica",
    "Guides, data, training, and hands-on support.": "Guías, datos, capacitación y apoyo práctico.",
    "Examples from other communities": "Ejemplos de otras comunidades",
    "Source-backed examples to help teams compare approaches and ask better questions.": "Ejemplos con fuentes para comparar enfoques y hacer mejores preguntas.",
    "Try fewer answers or a wider search.": "Pruebe con menos respuestas o una búsqueda más amplia.",
    "No matches yet": "Aún no hay opciones",
    "Clear one or more answers, or turn on closed rounds to see future options.": "Borre una o más respuestas o incluya convocatorias cerradas para ver opciones futuras.",
    "These are starting points. Add community details and priorities to rank them for your needs.": "Estos son puntos de partida. Agregue datos y prioridades de la comunidad para ordenarlos según sus necesidades.",
    "Try fewer choices or a wider search.": "Pruebe con menos opciones o una búsqueda más amplia."
  };

  const ATTRIBUTE_ES = {
    "Example: Taos": "Ejemplo: Taos",
    "Trail, downtown, business, water": "Sendero, centro, empresa, agua",
    "Example: Riverfront trail connection": "Ejemplo: conexión del sendero ribereño",
    "Add goals, partners, or next steps. Notes stay on this device unless you export them.": "Agregue metas, socios o próximos pasos. Las notas permanecen en este dispositivo salvo que las exporte.",
    "RERC-e, a bald eagle field guide holding a notebook at a rural trailhead": "RERC-e, un águila calva con un cuaderno al inicio de un sendero rural",
    "Program and site tools": "Herramientas del programa y del sitio",
    "Explorer catalog summary": "Resumen del catálogo",
    "Community planning steps": "Pasos de planificación comunitaria",
    "Choose what to show": "Elegir qué mostrar",
    "Match totals": "Totales de opciones",
    "Quick match exports": "Exportaciones rápidas",
    "Matching catalog records": "Registros del catálogo que coinciden",
    "Explorer navigation": "Navegación del explorador",
    "Close language menu": "Cerrar menú de idioma",
    "Close comparison": "Cerrar comparación",
    "Close sharing": "Cerrar ventana para compartir",
    "Share this workspace": "Compartir este espacio de trabajo",
    "Locate community on map": "Ubicar la comunidad en el mapa",
    "Map of the selected community": "Mapa de la comunidad seleccionada",
    "Close saved matches": "Cerrar opciones guardadas"
  };

  function translateTemplate(value) {
    if (ES[value]) return ES[value];
    let match = value.match(/^(\d[\d,.]*) matches$/);
    if (match) return match[1] === "1" ? "1 opción" : `${match[1]} opciones`;
    match = value.match(/^No (funding|resources|case studies) matches$/i);
    if (match) {
      const labels = { funding: "financiamiento", resources: "recursos", "case studies": "casos prácticos" };
      return `No hay opciones de ${labels[match[1].toLowerCase()]}`;
    }
    match = value.match(/^(Funding, resources, and case studies|Funding|Resources|Case studies) for (.+)$/);
    if (match) {
      const labels = {
        "Funding, resources, and case studies": "Financiamiento, recursos y casos prácticos",
        Funding: "Financiamiento",
        Resources: "Recursos",
        "Case studies": "Casos prácticos"
      };
      return `${labels[match[1]]} para ${match[2]}`;
    }
    match = value.match(/^(\d+) total matches; (\d+) cards displayed for (.+)\.$/);
    if (match) return `${match[1]} opciones en total; se muestran ${match[2]} tarjetas para ${match[3]}.`;
    match = value.match(/^Search: (.+)$/);
    if (match) return `Búsqueda: ${match[1]}`;
    match = value.match(/^(\d+) results?$/);
    if (match) return match[1] === "1" ? "1 resultado" : `${match[1]} resultados`;
    match = value.match(/^(\d+) applicant choices?$/);
    if (match) return match[1] === "1" ? "1 opción de solicitante" : `${match[1]} opciones de solicitante`;
    match = value.match(/^(\d+) topics?$/);
    if (match) return match[1] === "1" ? "1 tema" : `${match[1]} temas`;
    match = value.match(/^Save (.+)$/);
    if (match) return `Guardar ${match[1]}`;
    match = value.match(/^Compare (.+)$/);
    if (match) return `Comparar ${match[1]}`;
    match = value.match(/^(.+): (.+) \(opens in a new tab\)$/);
    if (match) return `${translateTemplate(match[1])}: ${match[2]} (se abre en una pestaña nueva)`;
    match = value.match(/^County or county equivalent \(([\d,]+)\)$/);
    if (match) return `Condado o equivalente (${match[1]})`;
    match = value.match(/^Town, city, or Census place \(([\d,]+)\)$/);
    if (match) return `Pueblo, ciudad o lugar del Censo (${match[1]})`;
    match = value.match(/^Choose a (county or county equivalent|town, city, or Census place)$/);
    if (match) return match[1].startsWith("county") ? "Elija un condado o equivalente" : "Elija un pueblo, ciudad o lugar del Censo";
    match = value.match(/^Choose from ([\d,]+) (county or county equivalent|town, city, or Census place)s?\.$/);
    if (match) return `Elija entre ${match[1]} ${match[2].startsWith("county") ? "condados o equivalentes" : "pueblos, ciudades o lugares del Censo"}.`;
    match = value.match(/^(\d+) funding matches shown in calendar view for (.+)\.$/);
    if (match) return `${match[1]} opciones de financiamiento en el calendario para ${match[2]}.`;
    match = value.match(/^(\d+) upcoming dates\. (\d+) rolling or ongoing\. (\d+) dates to confirm\.$/);
    if (match) return `${match[1]} fechas próximas. ${match[2]} continuas o sin fecha fija. ${match[3]} fechas por confirmar.`;
    match = value.match(/^(\d+) rolling or ongoing funding options$/);
    if (match) return `${match[1]} opciones continuas o sin fecha fija`;
    match = value.match(/^(\d+) options need a new cycle date; use the official program links to confirm timing\.$/);
    if (match) return `${match[1]} opciones necesitan una nueva fecha; confirme el plazo en el enlace oficial.`;
    match = value.match(/^No upcoming dated funding deadlines are available\. (\d+) options are rolling or ongoing; (\d+) need a new cycle date\.$/);
    if (match) return `No hay próximas fechas anunciadas. ${match[1]} opciones son continuas o no tienen fecha fija; ${match[2]} necesitan una nueva fecha.`;
    return value;
  }

  function translateTextNode(node) {
    if (!node || !node.parentElement || node.parentElement.closest("script, style")) return;
    if (!originalText.has(node)) originalText.set(node, node.nodeValue);
    const source = originalText.get(node);
    if (language === "en") {
      if (node.nodeValue !== source) node.nodeValue = source;
      return;
    }
    const leading = source.match(/^\s*/)[0];
    const trailing = source.match(/\s*$/)[0];
    const core = source.trim();
    if (!core) return;
    const translated = translateTemplate(core);
    const next = leading + translated + trailing;
    if (node.nodeValue !== next) node.nodeValue = next;
  }

  function translateAttributes(element) {
    if (!(element instanceof HTMLElement)) return;
    const names = ["placeholder", "aria-label", "title", "alt"];
    if (!originalAttributes.has(element)) originalAttributes.set(element, {});
    const sources = originalAttributes.get(element);
    names.forEach((name) => {
      if (!element.hasAttribute(name)) return;
      if (!(name in sources)) sources[name] = element.getAttribute(name);
      const source = sources[name];
      const next = language === "es"
        ? (ATTRIBUTE_ES[source] || translateTemplate(source))
        : source;
      if (element.getAttribute(name) !== next) element.setAttribute(name, next);
    });
  }

  function apply(root) {
    const scope = root && root.nodeType === Node.ELEMENT_NODE ? root : document.body;
    if (!scope) return;
    translateAttributes(scope);
    scope.querySelectorAll("*").forEach(translateAttributes);
    const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) translateTextNode(node);
  }

  function setLanguage(nextLanguage) {
    language = nextLanguage === "es" ? "es" : "en";
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    apply(document.body);
  }

  function initialize() {
    setLanguage(localStorage.getItem(LANGUAGE_KEY));
    if (!window.MutationObserver) return;
    observer = new MutationObserver((mutations) => {
      if (language !== "es") return;
      window.requestAnimationFrame(() => {
        mutations.forEach((mutation) => {
          if (mutation.type === "characterData") translateTextNode(mutation.target);
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.TEXT_NODE) translateTextNode(node);
            if (node.nodeType === Node.ELEMENT_NODE) apply(node);
          });
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  window.RERCI18N = { apply, setLanguage, getLanguage: () => language };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
}());
