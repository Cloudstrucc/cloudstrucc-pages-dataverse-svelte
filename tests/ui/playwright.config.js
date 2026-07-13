// @ts-check
const { defineConfig, devices } = require("@playwright/test");

// Two projects run the SAME spec files against two different targets:
//   - "wireframes"   -> tests/../wireframes/*.html   (POC, edit + approve here first)
//   - "webresources" -> src/**/*.html                (shipped Dataverse web resources)
//
// Specs resolve which file to load via tests/ui/pages.js#pageUrl(name, projectName).
// See docs/TESTING.md for the wireframe-first UI change workflow this supports.
module.exports = defineConfig({
  testDir: __dirname,
  testMatch: /.*\.spec\.js/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"]],
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "wireframes",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "webresources",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
