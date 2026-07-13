// Logical-page -> {wireframe, webresource} absolute file path map.
//
// This is the single source of truth for the wireframe-first UI testing
// workflow described in docs/TESTING.md:
//   1. A UI change is made to the file under `wireframe` first.
//   2. The relevant spec in tests/ui/*.spec.js is run against the
//      `wireframes` Playwright project and the change is reviewed/approved.
//   3. The same edit is ported to the file under `webresource`.
//   4. The same spec is run against the `webresources` Playwright project
//      to confirm the shipped web resource matches the approved wireframe.
//
// Both projects run the exact same spec files (see playwright.config.js);
// only the resolved file path differs, via the PAGES map below.

const path = require("node:path");

const ROOT = path.resolve(__dirname, "..", "..");

function abs(relativePath) {
  return path.join(ROOT, relativePath);
}

/**
 * @typedef {{ wireframe: string, webresource: string }} PagePaths
 */

/** @type {Record<string, PagePaths>} */
const PAGES = {
  admin: {
    wireframe: abs("wireframes/admin.html"),
    webresource: abs("src/admin-webresource/index.html"),
  },
  "studio-bootstrap": {
    wireframe: abs("wireframes/studio-bootstrap.html"),
    webresource: abs("src/studio-webresources/studio-bootstrap.html"),
  },
  "studio-gcdesign": {
    wireframe: abs("wireframes/studio-gcweb.html"),
    webresource: abs("src/studio-webresources/studio-gcdesign.html"),
  },
  "studio-landwind": {
    wireframe: abs("wireframes/studio-tailwind.html"),
    webresource: abs("src/studio-webresources/studio-landwind.html"),
  },
};

/**
 * Resolve a logical page name to a file:// URL for the given stage.
 * @param {string} pageName key of PAGES
 * @param {"wireframes"|"webresources"} stage Playwright project name
 * @returns {string}
 */
function pageUrl(pageName, stage) {
  const entry = PAGES[pageName];
  if (!entry) {
    throw new Error(`Unknown UI test page: ${pageName}`);
  }
  const key = stage === "webresources" ? "webresource" : "wireframe";
  const filePath = entry[key];
  return "file://" + filePath;
}

module.exports = { PAGES, pageUrl };
