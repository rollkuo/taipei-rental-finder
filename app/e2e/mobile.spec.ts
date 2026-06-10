import { expect, test } from "@playwright/test";

test("mobile viewport renders without overflow + screenshot artifact", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "台北租屋彙整" })).toBeVisible();

  // Verify the page doesn't have horizontal overflow (a common mobile bug)
  const overflow = await page.evaluate(() => {
    const w = document.documentElement;
    return { scrollWidth: w.scrollWidth, clientWidth: w.clientWidth };
  });
  expect(overflow.scrollWidth, "no horizontal overflow on mobile").toBeLessThanOrEqual(
    overflow.clientWidth + 1
  );

  // Confirm CSS viewport reports a narrow width — catches missing viewport meta tag.
  const cssWidth = await page.evaluate(() => window.innerWidth);
  expect(cssWidth, "CSS viewport should reflect device width <= 500px").toBeLessThanOrEqual(500);

  // Confirm cards are stacked single-column (Tailwind grid-cols-1 active on mobile)
  // by checking that no two cards share a row Y-coordinate.
  const yPositions = await page.locator("ul > li").evaluateAll((els) =>
    els.map((el) => Math.round((el as HTMLElement).getBoundingClientRect().top))
  );
  const uniqueYs = new Set(yPositions);
  expect(
    uniqueYs.size,
    "each card should be on its own row on mobile (1-col grid)"
  ).toBe(yPositions.length);

  // Floating + button must be reachable (in viewport)
  await expect(page.getByRole("button", { name: "手動加入物件" })).toBeInViewport();

  await page.screenshot({ path: "playwright-report/mobile-home.png", fullPage: true });
});
