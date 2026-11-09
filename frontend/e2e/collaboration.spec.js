import { expect, test } from "@playwright/test";
import { createDocument, editor, newUserPage, shareWith, typeInEditor } from "./helpers.js";

test("two users edit the same document in real time", async ({ browser }) => {
  const sara = await newUserPage(browser, "Sara");
  const mila = await newUserPage(browser, "Mila");

  await createDocument(mila.page, "خطة الفريق");
  await shareWith(mila.page, sara.user.email, "editor");

  // Sara finds it under "shared with me".
  await sara.page.getByRole("tab", { name: "مشتركة معي" }).click();
  await sara.page.getByRole("link", { name: /خطة الفريق/ }).click();
  await expect(sara.page.getByText("متصل · يُحفظ تلقائيًا")).toBeVisible();

  await typeInEditor(mila.page, "مرحبًا من ميلا.");
  await expect(editor(sara.page)).toContainText("مرحبًا من ميلا.");

  await typeInEditor(sara.page, " وسارة ترد.");
  await expect(editor(mila.page)).toContainText("وسارة ترد.");

  // Presence: both avatars, and Sara's named caret on Mila's screen.
  await expect(mila.page.getByText("2 متصلون الآن")).toBeVisible();
  await expect(mila.page.locator(".collaboration-carets__label", { hasText: "Sara" })).toBeVisible();

  // The content is saved: it is still there after a reload.
  await mila.page.waitForTimeout(2500);
  await mila.page.reload();
  await expect(editor(mila.page)).toContainText("مرحبًا من ميلا. وسارة ترد.");
});

test("a viewer is read-only, and loses access at once when removed", async ({ browser }) => {
  const omar = await newUserPage(browser, "Omar");
  const mila = await newUserPage(browser, "Mila");

  const url = await createDocument(mila.page, "تقرير سري");
  await typeInEditor(mila.page, "للقراءة فقط.");
  await shareWith(mila.page, omar.user.email, "viewer");

  await omar.page.goto(url);
  await expect(omar.page.getByText("👁 للقراءة فقط")).toBeVisible();
  await expect(editor(omar.page)).toContainText("للقراءة فقط.");
  await expect(editor(omar.page)).toHaveAttribute("contenteditable", "false");
  await expect(omar.page.getByRole("toolbar")).toHaveCount(0);

  // The owner removes Omar: his page reacts without a refresh.
  await mila.page.getByRole("button", { name: "مشاركة", exact: true }).click();
  await mila.page.getByRole("button", { name: "إزالة Omar" }).click();
  await expect(omar.page.getByRole("heading", { name: "المستند غير موجود" })).toBeVisible();
});
