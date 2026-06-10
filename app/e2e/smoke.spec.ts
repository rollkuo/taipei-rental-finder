import { expect, test } from "@playwright/test";

test.describe("smoke — page loads and shows controls", () => {
  test("header + filter chips + last-run text render", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));

    await page.goto("/");

    await expect(page.getByRole("heading", { name: "台北租屋彙整" })).toBeVisible();
    await expect(page.getByText("3 房以上")).toBeVisible();
    await expect(page.getByRole("button", { name: "信義區" })).toBeVisible();
    await expect(page.getByRole("button", { name: "大安區" })).toBeVisible();
    await expect(page.getByRole("button", { name: "中正區" })).toBeVisible();
    await expect(page.getByText(/上次抓取/)).toBeVisible();
    await expect(page.getByRole("button", { name: "手動加入物件" })).toBeVisible();

    // Fail the test if there were any console errors during load
    expect(consoleErrors, `console errors:\n${consoleErrors.join("\n")}`).toHaveLength(0);
  });

  test("default filter shows 信義區 + 大安區 active, others inactive", async ({ page }) => {
    await page.goto("/");
    const xinyi = page.getByRole("button", { name: "信義區" });
    const daan = page.getByRole("button", { name: "大安區" });
    const zhongzheng = page.getByRole("button", { name: "中正區" });
    // active = blue bg (bg-blue-600); inactive = grey (bg-zinc-100)
    await expect(xinyi).toHaveClass(/bg-blue-600/);
    await expect(daan).toHaveClass(/bg-blue-600/);
    await expect(zhongzheng).toHaveClass(/bg-zinc-100/);
  });
});
