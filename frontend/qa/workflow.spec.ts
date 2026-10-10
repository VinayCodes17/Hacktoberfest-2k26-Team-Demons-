import { test, expect } from "@playwright/test";
import path from "node:path";

const workbook = "C:/Users/VINAY/Downloads/HisabhParakh_Organizer_Aligned_500_Transactions.xlsx";

test("full workbook uploads through the frontend and shows mapping", async ({page}, info) => {
  await page.goto("/");
  await expect(page.getByRole("button", {name: "Inspect workbook", exact:true})).toBeDisabled();
  await page.getByLabel("Excel workbook", {exact:true}).setInputFiles(workbook);
  await page.getByRole("button", {name: "Inspect workbook", exact:true}).click();
  await expect(page.getByRole("heading", {name:"Workbook inspected"})).toBeVisible({timeout:60000});
  await expect(page.getByText("500", {exact:true})).toBeVisible();
  await expect(page.getByText("Organizer_Ready_Input", {exact:true})).toBeVisible();
  await page.getByText("Inspect column mapping", {exact:false}).click();
  await expect(page.getByRole("columnheader", {name:"Excel column"})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator(".classifier").screenshot({path:`../storage/qa/workflow-mapping-${info.project.name}.png`});
});

test("live one-row classification survives refresh and downloads Excel", async ({page}, info) => {
  test.skip(info.project.name !== "desktop", "Run live inference once; responsive mapping is tested in both views.");
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("Excel workbook", {exact:true}).setInputFiles(path.resolve("../storage/qa/worker-live-fixture.xlsx"));
  await page.getByRole("button", {name:"Inspect workbook",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Workbook inspected"})).toBeVisible({timeout:30000});
  await page.getByRole("button", {name:"Confirm mapping and classify"}).click();
  await expect(page.getByRole("heading", {name:/Classifying and checking evidence|Your results are ready/})).toBeVisible({timeout:10000});
  await page.reload();
  await expect(page.getByRole("heading", {name:"Your results are ready"})).toBeVisible({timeout:150000});
  await expect(page.getByText("1 of 1 rows processed", {exact:true})).toBeVisible();
  await page.getByRole("button", {name:"Needs review",exact:true}).click();
  await expect(page.locator(".result-row")).toHaveCount(1);
  const pending = page.waitForEvent("download");
  await page.getByRole("button", {name:"Download Excel results"}).click();
  const download = await pending;
  expect(download.suggestedFilename()).toMatch(/-classified\.xlsx$/);
  await download.saveAs("../storage/qa/browser-classified.xlsx");
  await page.locator(".classifier").screenshot({path:"../storage/qa/workflow-results.png"});
  expect(errors).toEqual([]);
  await page.getByRole("button", {name:"Process another workbook"}).click();
  await expect(page.getByRole("button", {name:"Inspect workbook",exact:true})).toBeDisabled();
});


test("sparse mixed voucher workbook with blank answers reaches mapping", async ({page}) => {
  await page.goto("/");
  await page.getByLabel("Excel workbook", {exact:true}).setInputFiles("C:/Users/VINAY/Downloads/testing/01_Balanced_27_Classes.xlsx");
  await page.getByRole("button", {name:"Inspect workbook",exact:true}).click();
  await expect(page.getByRole("heading", {name:"Workbook inspected"})).toBeVisible({timeout:30000});
  await expect(page.getByText("54", {exact:true})).toBeVisible();
  await expect(page.getByText("Transactions", {exact:true})).toBeVisible();
  await expect(page.getByRole("button", {name:"Confirm mapping and classify"})).toBeEnabled();
  await expect(page.locator(".classifier").getByRole("alert")).toHaveCount(0);
});
