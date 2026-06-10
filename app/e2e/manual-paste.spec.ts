import { expect, test } from "@playwright/test";

import { admin, hardDelete } from "./_fixtures";

test.describe("Manual paste fallback (+ button → modal → submit)", () => {
  test("open modal, fill form, submit, listing appears via Realtime", async ({ page }) => {
    const testListingId = `99000${Math.floor(Math.random() * 1_000_000)
      .toString()
      .padStart(6, "0")}`;
    let createdRowId: string | null = null;

    try {
      await page.goto("/");

      // Open modal via floating + button
      await page.getByRole("button", { name: "手動加入物件" }).click();
      await expect(page.getByRole("heading", { name: "手動加入 591 物件" })).toBeVisible();

      // Fill form (test uses an unused 591 URL; OG fetch will fail and that's fine)
      await page.getByLabel("591 連結 *").fill(`https://rent.591.com.tw/${testListingId}.html`);
      await page.getByLabel("月租 *").fill("77000");
      await page.getByLabel("房").selectOption("3");
      await page.getByLabel("衛").selectOption("2");
      await page.getByLabel("行政區 *").selectOption("大安區");
      await page.getByLabel("路段（選填）").fill("E2E測試路");

      // Submit
      await page.getByRole("button", { name: "加入物件", exact: true }).click();

      // Modal closes on success
      await expect(page.getByRole("heading", { name: "手動加入 591 物件" })).toBeHidden({
        timeout: 10_000,
      });

      // Find DB row to confirm + grab id for cleanup
      const { data: row } = await admin
        .from("listings")
        .select("id, source, district, price")
        .eq("source", "591_manual")
        .eq("source_id", testListingId)
        .maybeSingle();
      expect(row, "manual listing should exist in DB").not.toBeNull();
      expect(row?.district).toBe("大安區");
      expect(row?.price).toBe(77000);
      createdRowId = row?.id ?? null;

      // Realtime should make it visible on the page (大安區 is in default filter)
      const card = page.locator("li").filter({ hasText: "E2E測試路" }).first();
      await expect(card).toBeVisible({ timeout: 5_000 });
    } finally {
      if (createdRowId) await hardDelete(createdRowId);
    }
  });

  test("submitting non-591 URL shows error and modal stays open", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "手動加入物件" }).click();
    await page.getByLabel("591 連結 *").fill("https://example.com/not-591");
    await page.getByLabel("月租 *").fill("50000");
    await page.getByRole("button", { name: "加入物件", exact: true }).click();

    await expect(page.getByText(/rent\.591\.com\.tw/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("heading", { name: "手動加入 591 物件" })).toBeVisible();
  });
});
