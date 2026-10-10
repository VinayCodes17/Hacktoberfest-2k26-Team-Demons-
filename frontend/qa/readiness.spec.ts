import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("live readiness, navigation, refresh and responsive layout", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "A clear view. A checked decision." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Database", exact: true })).toBeVisible();
  await expect(page.getByText("The local API isn’t connected.")).toHaveCount(0);
  await expect(page.getByText("Not ready yet", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Check workspace readiness" }).click();
  await expect(page).toHaveURL(/#readiness$/);
  await page.getByRole("link", { name: "Refresh checks" }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Database", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await page.evaluate(() => window.scrollTo(0, 0));
  await mkdir("../storage/qa", { recursive: true });
  await page.screenshot({ path: `../storage/qa/${info.project.name}.png`, fullPage: true });
});
