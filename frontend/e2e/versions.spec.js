import { expect, test } from "@playwright/test";
import { createDocument, editor, newUserPage, typeInEditor } from "./helpers.js";

test("save a version, restore it, and see it in the activity log", async ({ browser }) => {
  const { page } = await newUserPage(browser, "Mila");
  await createDocument(page, "مسودة");

  await typeInEditor(page, "الفقرة الأولى.");
  await page.getByRole("button", { name: "💾 الإصدارات" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("حفظ المحتوى الحالي كإصدار").fill("المسودة الأولى");
  await dialog.getByRole("button", { name: "حفظ إصدار" }).click();
  await expect(dialog.getByText("💾 المسودة الأولى")).toBeVisible();
  await dialog.getByRole("button", { name: "إغلاق" }).click();

  await typeInEditor(page, " نص سيُحذف.");
  await expect(editor(page)).toContainText("نص سيُحذف.");

  await page.getByRole("button", { name: "💾 الإصدارات" }).click();
  await dialog.getByText("💾 المسودة الأولى").click();
  await expect(dialog.locator(".version-preview-content")).toHaveText("الفقرة الأولى.");
  await dialog.getByRole("button", { name: "استرجاع هذا الإصدار" }).click();

  await expect(editor(page)).toHaveText("الفقرة الأولى.");

  // A backup of the replaced content was saved automatically.
  await page.getByRole("button", { name: "💾 الإصدارات" }).click();
  await expect(dialog.getByText("قبل استرجاع «المسودة الأولى»")).toBeVisible();
  await dialog.getByRole("button", { name: "إغلاق" }).click();

  await page.getByRole("button", { name: "🕒 النشاط" }).click();
  await expect(dialog.getByText("استرجع الإصدار «المسودة الأولى»")).toBeVisible();
  await expect(dialog.getByText("حفظ إصدارًا باسم «المسودة الأولى»")).toBeVisible();
  await expect(dialog.getByText("أنشأ المستند")).toBeVisible();
});
