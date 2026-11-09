import { expect } from "@playwright/test";

export const PASSWORD = "Collab#Space2026";

let counter = 0;
/** A unique test user (the database is wiped before every run). */
export function newUser(name) {
  counter += 1;
  return { name, email: `${name.toLowerCase()}.${Date.now()}.${counter}@example.com` };
}

/** Register through the real form; ends logged in on the dashboard. */
export async function register(page, user) {
  await page.goto("/register");
  await page.getByLabel("الاسم", { exact: true }).fill(user.name);
  await page.getByLabel("البريد الإلكتروني", { exact: true }).fill(user.email);
  await page.getByLabel("كلمة المرور", { exact: true }).fill(PASSWORD);
  await page.getByLabel("تأكيد كلمة المرور", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "إنشاء الحساب" }).click();
  await expect(page.getByRole("heading", { name: `أهلًا، ${user.name}` })).toBeVisible();
}

/** A separate browser (own cookies) with a newly registered user. */
export async function newUserPage(browser, name) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const user = newUser(name);
  await register(page, user);
  return { page, user, context };
}

export async function createDocument(page, title) {
  await page.getByRole("button", { name: "مستند جديد" }).click();
  await page.getByLabel("عنوان المستند").fill(title);
  await page.getByRole("button", { name: "إنشاء", exact: true }).click();
  await expect(page).toHaveURL(/\/documents\/[0-9a-f-]{36}$/);
  await expect(page.getByText("متصل · يُحفظ تلقائيًا")).toBeVisible();
  return page.url();
}

export async function shareWith(page, email, role) {
  await page.getByRole("button", { name: "مشاركة", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("البريد الإلكتروني").fill(email);
  await dialog.getByLabel("الدور", { exact: true }).selectOption(role);
  await dialog.getByRole("button", { name: "مشاركة", exact: true }).click();
  await expect(dialog.getByText(email)).toBeVisible();
  await dialog.getByRole("button", { name: "إغلاق" }).click();
}

/** The live editor (not the version preview). */
export const editor = (page) => page.locator(".editor-shell .editor-content");

export async function typeInEditor(page, text) {
  await editor(page).click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type(text);
}
