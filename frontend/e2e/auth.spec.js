import { expect, test } from "@playwright/test";
import { newUser, PASSWORD, register } from "./helpers.js";

test("register, log out, and log back in", async ({ page }) => {
  const user = newUser("Lina");
  await register(page, user);

  await page.getByRole("button", { name: "تسجيل الخروج" }).click();
  await expect(page).toHaveURL(/\/login$/);

  // Protected pages send visitors to the login page.
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(user.email);
  await page.getByLabel("كلمة المرور", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
  // ...and back to the page that was requested.
  await expect(page.getByRole("heading", { name: "الإعدادات" })).toBeVisible();
});

test("a wrong password shows an error", async ({ page }) => {
  const user = newUser("Omar");
  await register(page, user);
  await page.getByRole("button", { name: "تسجيل الخروج" }).click();

  await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(user.email);
  await page.getByLabel("كلمة المرور", { exact: true }).fill("not-the-password");
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
  await expect(page.getByText("البريد الإلكتروني أو كلمة المرور غير صحيحة.")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});
