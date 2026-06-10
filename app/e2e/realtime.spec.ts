import { expect, test } from "@playwright/test";

import { hardDelete, seedListing } from "./_fixtures";

test.describe("Realtime cross-device sync (the 1-3s sync requirement)", () => {
  test("save on device A → device B sees ⭐ within 8s", async ({ browser }) => {
    const seeded = await seedListing({
      district: "信義區",
      title: "[E2E] realtime-test 信義區三房",
    });
    const ctxA = await browser.newContext();
    const ctxB = await browser.newContext();
    const pageA = await ctxA.newPage();
    const pageB = await ctxB.newPage();

    // Capture WS / console messages from page B so we can see if Realtime fired
    const bMessages: string[] = [];
    pageB.on("console", (msg) => bMessages.push(`B:${msg.type()}: ${msg.text()}`));
    pageB.on("websocket", (ws) => {
      ws.on("framereceived", (frame) => {
        const data = String(frame.payload).slice(0, 200);
        if (data.includes("listings") || data.includes("saved_at"))
          bMessages.push(`B:ws-in: ${data}`);
      });
    });

    try {
      await Promise.all([pageA.goto("/"), pageB.goto("/")]);

      const cardA = pageA.locator("li").filter({ hasText: "realtime-test 信義區三房" });
      const cardB = pageB.locator("li").filter({ hasText: "realtime-test 信義區三房" });
      await expect(cardA).toBeVisible({ timeout: 10_000 });
      await expect(cardB).toBeVisible({ timeout: 10_000 });

      // Give Realtime channels time to subscribe (the websocket handshake +
      // server-side ack can take a couple of seconds on a fresh connection).
      await pageB.waitForTimeout(3_000);

      await cardA.getByRole("button", { name: /★ 收藏/ }).click();
      await expect(cardA.getByText("⭐ 已收藏")).toBeVisible({ timeout: 5_000 });

      await expect(cardB.getByText("⭐ 已收藏")).toBeVisible({ timeout: 8_000 });
    } catch (e) {
      console.error("=== device B messages ===");
      bMessages.forEach((m) => console.error(m));
      throw e;
    } finally {
      await ctxA.close();
      await ctxB.close();
      await hardDelete(seeded.id);
    }
  });

  test("delete on device A → device B sees card disappear within 8s", async ({ browser }) => {
    const seeded = await seedListing({
      district: "信義區",
      title: "[E2E] realtime-delete 信義區三房",
    });
    const ctxA = await browser.newContext();
    const ctxB = await browser.newContext();
    const pageA = await ctxA.newPage();
    const pageB = await ctxB.newPage();
    try {
      pageA.on("dialog", (d) => d.accept());
      await Promise.all([pageA.goto("/"), pageB.goto("/")]);

      const cardA = pageA.locator("li").filter({ hasText: "realtime-delete 信義區三房" });
      const cardB = pageB.locator("li").filter({ hasText: "realtime-delete 信義區三房" });
      await expect(cardA).toBeVisible({ timeout: 10_000 });
      await expect(cardB).toBeVisible({ timeout: 10_000 });

      // Wait for Supabase Realtime WebSocket subscribe handshake (~2s on cold connect).
      await pageB.waitForTimeout(3_000);

      await cardA.getByRole("button", { name: "刪除" }).click();

      await expect(cardA).toBeHidden({ timeout: 5_000 });
      await expect(cardB).toBeHidden({ timeout: 8_000 });
    } finally {
      await ctxA.close();
      await ctxB.close();
      await hardDelete(seeded.id);
    }
  });
});
