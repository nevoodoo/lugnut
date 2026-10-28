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

  // Reload and open the saved fill: this is what the server stored
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Australia/Sydney" }).format(new Date());
  await page.reload();
  await page.locator("a.rec").first().click();
  await expect(page.getByLabel("Date")).toHaveValue(today);
  await expect(page.getByLabel(/^Volume/)).toHaveValue("40");
  await expect(page.getByLabel("Cost", { exact: true })).toHaveValue("62.50");
  await expect(page.getByLabel(/^Odometer/)).toHaveValue("12345");
  await expect(page.getByLabel("Filled the tank")).toBeChecked();

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
  await page.getByLabel("Due date").fill(today);
  await page.getByRole("button", { name: "Save" }).click();
  await page.goto(vehicleUrl);
  await expect(page.getByText("Oil change")).toBeVisible();
  await expect(page.locator(".stamp.due")).toBeVisible();

  // The API agrees
  const res = await page.request.get("/api/reminders");
  expect(res.ok()).toBeTruthy();
  const reminders: { title: string; state: string }[] = await res.json();
  expect(reminders.find((r) => r.title === "Oil change")?.state).toBe("due");

  // Work record: two line items, one with qty 2, and an attached PDF
  await page.goto(`${vehicleUrl}/records/new?type=work`);
  await page.getByLabel("Workshop").fill("Joe's Garage");
  const lines = page.getByRole("listitem", { name: /^Line item/ });
  if ((await lines.count()) === 0) await page.getByRole("button", { name: "Add line" }).click();
  await page.getByRole("button", { name: "Add line" }).click();
  await expect(lines).toHaveCount(2);
  await lines.nth(0).getByLabel("Description").fill("Oil filter");
  await lines.nth(0).getByLabel("Cost each").fill("30.00");
  await lines.nth(0).getByLabel("Qty").fill("2");
  await lines.nth(1).getByLabel("Description").fill("Labour");
  await lines.nth(1).getByLabel("Cost each").fill("45.50");
  await page.locator('input[type="file"]').setInputFiles("e2e/invoice.pdf");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: "Records" })).toBeVisible();

  // Reload, reopen the record, check every line and the file
  await page.reload();
  await page.locator("a.rec", { hasText: "Joe's Garage" }).click();
  await expect(lines).toHaveCount(2);
  await expect(lines.nth(0).getByLabel("Description")).toHaveValue("Oil filter");
  await expect(lines.nth(0).getByLabel("Cost each")).toHaveValue("30.00");
  await expect(lines.nth(0).getByLabel("Qty")).toHaveValue("2");
  await expect(lines.nth(1).getByLabel("Description")).toHaveValue("Labour");
  await expect(lines.nth(1).getByLabel("Cost each")).toHaveValue("45.50");
  await expect(page.getByText(/Total/)).toContainText("105.50");
  await expect(page.getByRole("link", { name: "invoice.pdf" })).toBeVisible();
});
