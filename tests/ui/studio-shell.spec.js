// @ts-check
const { test, expect } = require("@playwright/test");
const { pageUrl } = require("./pages");

// The three studio themes share one JS/CSS shell (rail, panels, canvas,
// toolbar) with only theme-specific canvas content differing. This spec runs
// once per theme x {wireframes, webresources} project, so a shell regression
// in any theme surfaces immediately across all six combinations.
const THEMES = [
  { page: "studio-bootstrap", title: "Cloudstrucc Studio — Start Bootstrap Landing Page" },
  { page: "studio-gcdesign", title: "Cloudstrucc Studio — GC Design System Basic Page" },
  { page: "studio-landwind", title: "Cloudstrucc Studio — Landwind Tailwind / Flowbite" },
];

// On load the shell runs fitCanvasToArea() asynchronously (double
// requestAnimationFrame) to size the canvas to the viewport, which rewrites
// #zoomValue away from its static "100%" markup shortly after first paint.
// Reading the value too early races that adjustment, so poll until two
// consecutive reads agree before treating it as the settled starting point.
async function readStableZoomPercent(page) {
  const zoomValue = page.locator("#zoomValue");
  let previous = null;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const current = await zoomValue.textContent();
    if (current === previous) {
      return Number(current.replace("%", ""));
    }
    previous = current;
    await page.waitForTimeout(50);
  }
  return Number(previous.replace("%", ""));
}

const RAIL_PANELS = [
  "pages",
  "components",
  "design",
  "data",
  "identity",
  "permissions",
  "localization",
  "settings",
];

for (const theme of THEMES) {
  test.describe(`Studio shell — ${theme.page}`, () => {
    test.beforeEach(async ({ page }, testInfo) => {
      await page.goto(pageUrl(theme.page, testInfo.project.name));
    });

    test("loads with the expected document title", async ({ page }) => {
      await expect(page).toHaveTitle(theme.title);
    });

    test("renders the left rail with all panel entries, Pages active by default", async ({ page }) => {
      const railButtons = page.locator("[data-panel]");
      await expect(railButtons).toHaveCount(RAIL_PANELS.length);
      for (const panel of RAIL_PANELS) {
        await expect(page.locator(`[data-panel="${panel}"]`)).toHaveCount(1);
      }
      await expect(page.locator('[data-panel="pages"]')).toHaveClass(/active/);
      await expect(page.locator("#leftTitle")).toHaveText("Pages");
    });

    test("switching rail panels updates the active button and the left panel body", async ({ page }) => {
      await page.locator('[data-panel="components"]').click();

      await expect(page.locator('[data-panel="components"]')).toHaveClass(/active/);
      await expect(page.locator('[data-panel="pages"]')).not.toHaveClass(/active/);
      await expect(page.locator("#leftTitle")).toHaveText("Components");
      await expect(page.locator("#componentSearch")).toBeVisible();
    });

    test("EN/FR language toggle switches the active language button", async ({ page }) => {
      await expect(page.locator('[data-lang="en"]')).toHaveClass(/active/);
      await expect(page.locator('[data-lang="fr"]')).not.toHaveClass(/active/);

      await page.locator('[data-lang="fr"]').click();

      await expect(page.locator('[data-lang="fr"]')).toHaveClass(/active/);
      await expect(page.locator('[data-lang="en"]')).not.toHaveClass(/active/);
    });

    test("device preview buttons toggle the canvas viewport class", async ({ page }) => {
      const canvas = page.locator("#canvas");
      await expect(canvas).not.toHaveClass(/tablet/);
      await expect(canvas).not.toHaveClass(/mobile/);

      await page.locator('[data-device="tablet"]').click();
      await expect(canvas).toHaveClass(/tablet/);
      await expect(canvas).not.toHaveClass(/mobile/);

      await page.locator('[data-device="mobile"]').click();
      await expect(canvas).toHaveClass(/mobile/);
      await expect(canvas).not.toHaveClass(/tablet/);

      await page.locator('[data-device="desktop"]').click();
      await expect(canvas).not.toHaveClass(/tablet/);
      await expect(canvas).not.toHaveClass(/mobile/);
    });

    test("zoom controls step the readout by 10 percentage points and back", async ({ page }) => {
      // The initial value is whatever fitCanvasToArea() computes for the
      // viewport on load (not a fixed 100%), so this asserts the relative
      // step behavior rather than an absolute starting value.
      const zoomValue = page.locator("#zoomValue");
      const initial = await readStableZoomPercent(page);
      expect(Number.isFinite(initial)).toBe(true);

      await page.locator("#zoomIn").click();
      await expect(zoomValue).toHaveText(`${Math.min(150, initial + 10)}%`);

      await page.locator("#zoomOut").click();
      await expect(zoomValue).toHaveText(`${initial}%`);
    });

    test("collapse buttons hide each panel and its restore tab brings it back", async ({ page }) => {
      const workspace = page.locator("#workspace");
      await expect(workspace).not.toHaveClass(/left-collapsed/);
      await expect(workspace).not.toHaveClass(/right-collapsed/);

      // Collapsing hides the in-panel collapse button itself; the app
      // surfaces a dedicated restore tab to reopen the panel instead of
      // re-showing the same control.
      await page.locator("#collapseLeft").click();
      await expect(workspace).toHaveClass(/left-collapsed/);
      await expect(page.locator("#leftRestoreTab")).toBeVisible();

      await page.locator("#leftRestoreTab").click();
      await expect(workspace).not.toHaveClass(/left-collapsed/);

      await page.locator("#collapseRight").click();
      await expect(workspace).toHaveClass(/right-collapsed/);
      await expect(page.locator("#rightRestoreTab")).toBeVisible();

      await page.locator("#rightRestoreTab").click();
      await expect(workspace).not.toHaveClass(/right-collapsed/);
    });

    test("Publish opens a confirmation modal that can be dismissed", async ({ page }) => {
      await page.locator("#publishBtn").click();

      const dialog = page.locator("#modalHost .dialog");
      await expect(dialog).toBeVisible();
      await expect(dialog.locator("h2")).toHaveText("Publish site");
      await expect(page.locator("#applyModal")).toBeVisible();

      await page.locator("#closeModal").click();
      await expect(page.locator("#modalHost .dialog")).toHaveCount(0);
    });

    test("Preview opens an in-canvas preview overlay that can be closed", async ({ page }) => {
      await page.locator("#previewBtn").click();

      await expect(page.locator("#previewMode")).toBeVisible();

      await page.locator("#previewClose").click();
      await expect(page.locator("#previewMode")).toHaveCount(0);
    });
  });
}
