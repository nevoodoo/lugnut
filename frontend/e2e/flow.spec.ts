import { expect, test } from "@playwright/test";

test("required flow: add vehicle, log fuel, reminder fires", async ({ page }) => {
  // Setup
  await page.goto("/");
  await page.getByLabel("Username").fill("owner");
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Set up your account" })).toBeHidden();

  // Add a vehicle
  await page.goto("/vehicles/new");
  await page.getByLabel("Name").fill("Daily Civic");
  await page.getByLabel("Year").fill("2014");
  await page.getByLabel("Make").fill("Honda");
  await page.getByLabel("Model").fill("Civic");
  await page.getByLabel("Plate").fill("ABC123");
  await page.getByLabel("Fuel type").selectOption("petrol");
  await page.getByLabel("VIN").fill("JHMFK2630EX000001");
  await page.getByLabel("Colour").fill("Blue");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Daily Civic" })).toBeVisible();
  const vehicleUrl = page.url();

  // Quick fuel
  await page.getByRole("link", { name: "Log fuel" }).click();
  await page.getByLabel(/^Volume/).fill("40");
  await page.getByLabel("Cost").fill("62.50");
  await page.getByLabel(/^Odometer/).fill("12345");
  await page.getByRole("button", { name: "Save fill" }).click();
  await expect(page.getByRole("heading", { name: "Daily Civic" })).toBeVisible();
  await expect(page.getByText("12,345").first()).toBeVisible();

  // Reopen the vehicle and check every field
  await page.goto(`${vehicleUrl}/edit`);
  await expect(page.getByLabel("Name")).toHaveValue("Daily Civic");
  await expect(page.getByLabel("Year")).toHaveValue("2014");
  await expect(page.getByLabel("Make")).toHaveValue("Honda");
  await expect(page.getByLabel("Model")).toHaveValue("Civic");
  await expect(page.getByLabel("Plate")).toHaveValue("ABC123");
  await expect(page.getByLabel("Fuel type")).toHaveValue("petrol");
  await expect(page.getByLabel("VIN")).toHaveValue("JHMFK2630EX000001");
  await expect(page.getByLabel("Colour")).toHaveValue("Blue");

  // Reminder due today
  await page.goto(`${vehicleUrl}/reminders/new`);
  await page.getByLabel("Title").fill("Oil change");
  await page.getByLabel("Due date").fill(new Date().toLocaleDateString("en-CA"));
  await page.getByRole("button", { name: "Save" }).click();
  await page.goto(vehicleUrl);
  await expect(page.getByText("Oil change")).toBeVisible();
  await expect(page.locator(".stamp.due")).toBeVisible();

  // The API agrees
  const res = await page.request.get("/api/reminders");
  expect(res.ok()).toBeTruthy();
  const reminders = await res.json();
  expect(JSON.stringify(reminders)).toContain('"state":"due"');
});
