import { test, expect } from "@playwright/test";

test("login page loads", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

test("employee can login and see sales nav", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("agent1@gmail.com");
  await page.getByLabel(/password/i).fill("Agent@123");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /overview/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Leads" })).toBeVisible();
  await expect(page.getByRole("link", { name: "My Tasks" })).toBeVisible();
  await page.getByRole("link", { name: "My Tasks" }).click();
  await expect(page.getByRole("heading", { name: /my tasks/i })).toBeVisible();
});
