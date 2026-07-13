// @ts-check
const { test, expect } = require("@playwright/test");
const { pageUrl } = require("./pages");

// Runs identically against the "wireframes" and "webresources" Playwright
// projects (see playwright.config.js). The project name IS the stage.
// `label` is the sidebar button text. `header` is what the top bar shows
// after navigating there: admin.html's render(v) sets the header from the
// raw data-view key (capitalized), NOT from the button label, so the two
// intentionally diverge for multi-word entries (e.g. "identity" -> "Identity",
// not "Identity providers"). Both are asserted below so a future refactor
// that makes the header show the full label is a deliberate, visible change.
const NAV_ITEMS = [
  { view: "overview", label: "Overview", header: "Overview" },
  { view: "websites", label: "Websites", header: "Websites" },
  { view: "domains", label: "Domains", header: "Domains" },
  { view: "identity", label: "Identity providers", header: "Identity" },
  { view: "connections", label: "Connections", header: "Connections" },
  { view: "permissions", label: "Permissions", header: "Permissions" },
  { view: "solutions", label: "Solutions & ALM", header: "Solutions" },
  { view: "environments", label: "Environments", header: "Environments" },
  { view: "audit", label: "Audit logs", header: "Audit" },
];

test.describe("Admin console shell", () => {
  test.beforeEach(async ({ page }, testInfo) => {
    await page.goto(pageUrl("admin", testInfo.project.name));
  });

  test("loads with the expected document title", async ({ page }) => {
    await expect(page).toHaveTitle("Cloudstrucc Pages Administration");
  });

  test("renders the sidebar with all navigation entries, Overview active by default", async ({ page }) => {
    const navButtons = page.locator(".nav button[data-view]");
    await expect(navButtons).toHaveCount(NAV_ITEMS.length);

    for (const item of NAV_ITEMS) {
      await expect(page.locator(`.nav button[data-view="${item.view}"]`)).toHaveText(item.label);
    }

    await expect(page.locator('.nav button[data-view="overview"]')).toHaveClass(/active/);
    await expect(page.locator("#title")).toHaveText("Overview");
  });

  test("shows the primary Create website action on every load", async ({ page }) => {
    await expect(page.locator("#newSite")).toBeVisible();
    await expect(page.locator("#newSite")).toHaveText("Create website");
  });

  for (const item of NAV_ITEMS) {
    test(`navigating to "${item.label}" activates that section and updates the header`, async ({ page }) => {
      await page.locator(`.nav button[data-view="${item.view}"]`).click();

      await expect(page.locator(`.nav button[data-view="${item.view}"]`)).toHaveClass(/active/);
      await expect(page.locator("#title")).toHaveText(item.header);

      // Exactly one nav button should carry the active class at a time.
      await expect(page.locator(".nav button.active")).toHaveCount(1);

      // The content region should render something for the section (never blank).
      await expect(page.locator("#content")).not.toBeEmpty();
    });
  }

  test("Create website opens a modal with site fields and a 3-option theme picker", async ({ page }) => {
    await page.locator("#newSite").click();

    const dialog = page.locator(".modal .dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.locator("h2")).toHaveText("Create Cloudstrucc website");

    await expect(page.locator("#siteName")).toHaveValue("New Digital Service");
    await expect(page.locator("#createFrench")).toBeChecked();

    const themes = page.locator(".theme");
    await expect(themes).toHaveCount(3);
    await expect(page.locator('.theme[data-theme="bootstrap"]')).toHaveClass(/selected/);
    await expect(page.locator('.theme[data-theme="landwind"]')).not.toHaveClass(/selected/);
    await expect(page.locator('.theme[data-theme="gc"]')).not.toHaveClass(/selected/);

    await expect(page.locator(".preview-theme")).toHaveCount(3);
    await expect(page.locator("#provision")).toBeVisible();
    await expect(page.locator("#provision")).toHaveText("Provision website");
  });

  test("selecting a different theme card marks it selected and clears the others", async ({ page }) => {
    await page.locator("#newSite").click();

    await page.locator('.theme[data-theme="landwind"]').click();

    await expect(page.locator('.theme[data-theme="landwind"]')).toHaveClass(/selected/);
    await expect(page.locator('.theme[data-theme="bootstrap"]')).not.toHaveClass(/selected/);
    await expect(page.locator('.theme[data-theme="gc"]')).not.toHaveClass(/selected/);
  });

  test("the modal close control (×) dismisses the Create website dialog", async ({ page }) => {
    await page.locator("#newSite").click();
    await expect(page.locator(".modal .dialog")).toBeVisible();

    await page.locator(".head button", { hasText: "×" }).click();

    await expect(page.locator(".modal")).toHaveCount(0);
  });

  test("Cancel in the Create website footer dismisses the dialog without provisioning", async ({ page }) => {
    await page.locator("#newSite").click();
    await page.locator(".foot button", { hasText: "Cancel" }).click();

    await expect(page.locator(".modal")).toHaveCount(0);
  });
});
