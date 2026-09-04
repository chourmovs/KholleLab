import { expect, test } from "@playwright/test";
test("blackboard is responsive on desktop and mobile",async({page})=>{await page.goto("/");await expect(page.locator("body")).not.toHaveCSS("overflow-x","scroll");});
