"use strict";

// EPA maintainers can adjust public filters and match ranking here without changing app.js.
window.RERC_SITE_CONFIG = {
  schemaVersion: 1,
  geography: {
    regionalCoverageField: "covered_states",
    failClosedWithoutRegionalCoverage: true
  },
  filters: {
    applicants: [
      ["local government|local governments|municipal|municipality|municipalities|county|counties|city|cities|town|towns|village|villages|political subdivision|political subdivisions", "Local government"],
      ["tribe|tribes|tribal|native|indian nation|indian nations|sovereign", "Tribe or Native community"],
      ["nonprofit|nonprofits|non-profit|non-profits|community organization|community organizations|land trust|land trusts", "Nonprofit or community group"],
      ["state agency|state agencies|state government", "State agency"],
      ["business|businesses|entrepreneur|entrepreneurs|tourism|destination marketing|convention|visitors bureau|visitor bureau", "Business or tourism group"],
      ["school|schools|college|colleges|university|universities|library|libraries|museum|museums", "School, library, or museum"],
      ["utility|utilities|authority|authorities|district|districts", "Utility or public authority"],
      ["landowner|landowners|individual|individuals|families", "Landowner or individual"],
      ["eligible|applicant|applicants|public agency|public agencies|sponsor|sponsors|organization|organizations|customer|customers|owner|owners|student|students|farmer|farmers|fishermen|worker|workers|sportsmen|resident|residents|member|members|partner|partners|representative|representatives|planner|planners|consultant|consultants|recipient|recipients|institution|institutions|entity|entities|government|governments|community|communities|state|states|varies|see program|check with the program", "Other or varies by program"]
    ],
    topics: [
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
    ],
    stages: ["Any step", "Planning", "Early Design", "Engineering", "Construction", "Implementation", "Operations/Maintenance", "Capacity Building", "Acquisition", "Cleanup"]
  },
  ranking: {
    thresholds: { high: 80, medium: 65 },
    base: { funding: 45, resource: 45, caseStudy: 52 },
    weights: {
      available: 18,
      recurring: 14,
      closed: -18,
      selectedState: 15,
      nationwide: 8,
      regional: 12,
      applicant: 12,
      topicEach: 7,
      topicMaximum: 18,
      exactStage: 10,
      mixedStage: 4,
      summary: 3,
      caseState: 18,
      caseTopicEach: 7,
      caseTopicMaximum: 21,
      caseStage: 8,
      caseSource: 5
    }
  }
};