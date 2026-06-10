import { expect, test } from "@playwright/test";

import { hardDelete, readListing, seedListing } from "./_fixtures";

test.describe("save / unsave / soft-delete flows", () => {
  test("click 收藏 → saved_at written → 取消收藏 → cleared", async ({ page }) => {
    const seeded = await seedListing({ district: "信義區", title: "[E2E] save-test 信義區三房" });
    try {
      await page.goto("/");
      const card = page.locator("li").filter({ hasText: "save-test 信義區三房" });
      await expect(card).toBeVisible({ timeout: 10_000 });

      // Click 收藏
      await card.getByRole("button", { name: /★ 收藏/ }).click();

      // Optimistic UI: badge appears
      await expect(card.getByText("⭐ 已收藏")).toBeVisible({ timeout: 5_000 });

      // DB must reflect within a few seconds
      let saved: string | null = null;
      for (let i = 0; i < 10; i++) {
        const row = await readListing(seeded.id);
        if (row?.saved_at) {
          saved = row.saved_at;
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
      expect(saved, "saved_at should be set in DB").not.toBeNull();

      // Toggle off
      await card.getByRole("button", { name: "取消收藏" }).click();
      await expect(card.getByText("⭐ 已收藏")).toBeHidden({ timeout: 5_000 });

      for (let i = 0; i < 10; i++) {
        const row = await readListing(seeded.id);
        if (!row?.saved_at) return;
        await new Promise((r) => setTimeout(r, 500));
      }
      throw new Error("saved_at was not cleared in DB after unsave");
    } finally {
      await hardDelete(seeded.id);
    }
  });

  test("click 刪除 (after confirm) → deleted_at written → card disappears", async ({ page }) => {
    const seeded = await seedListing({ district: "大安區", title: "[E2E] delete-test 大安區三房" });
    try {
      // Auto-accept the confirm() dialog before clicking
      page.on("dialog", (d) => d.accept());

      await page.goto("/");
      const card = page.locator("li").filter({ hasText: "delete-test 大安區三房" });
      await expect(card).toBeVisible({ timeout: 10_000 });

      await card.getByRole("button", { name: "刪除" }).click();

      // Card should disappear from UI (deleted_at filter)
      await expect(card).toBeHidden({ timeout: 5_000 });

      // DB row must have deleted_at populated
      let deleted: string | null = null;
      for (let i = 0; i < 10; i++) {
        const row = await readListing(seeded.id);
        if (row?.deleted_at) {
          deleted = row.deleted_at;
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
      expect(deleted, "deleted_at should be set in DB").not.toBeNull();
    } finally {
      await hardDelete(seeded.id);
    }
  });
});
