import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./qa",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "../storage/qa/browser-results.json" }]],
  use: { baseURL: process.env.QA_BASE_URL ?? "http://127.0.0.1:3000", channel: "chrome" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1050 } } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 1 } },
  ],
});
