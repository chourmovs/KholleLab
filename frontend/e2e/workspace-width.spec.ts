import {expect,test} from "@playwright/test";

const viewports=[{width:1440,height:900},{width:1024,height:900},{width:390,height:844}];
for(const viewport of viewports)test(`workspace remains structured at ${viewport.width}px`,async({page})=>{
  await page.setViewportSize(viewport);await page.goto("/");
  const main=page.locator("main");await expect(main).toBeVisible();
  const box=await main.boundingBox();expect(box).not.toBeNull();expect(box!.width).toBeLessThanOrEqual(1722);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width+2);
  await expect(page.getByRole("navigation",{name:"Outils du tableau"})).toBeVisible();
  await expect(page.locator(".professor-pane")).toBeVisible();
  if(viewport.width>=1200){
    const board=await page.locator(".blackboard-pane").boundingBox();
    const statement=await page.locator(".statement-pane").boundingBox();
    const professor=await page.locator(".professor-pane").boundingBox();
    expect(board!.width).toBeGreaterThan(statement!.width);expect(board!.width).toBeGreaterThan(professor!.width);
  }
});

test("l’énoncé compact se replie sans masquer l’espace de travail",async({page})=>{
  await page.goto("/");const toggle=page.locator(".problem-toggle");
  if(await toggle.count()){await expect(toggle).toHaveAttribute("aria-expanded","true");await toggle.click();await expect(toggle).toHaveAttribute("aria-expanded","false");await expect(page.locator(".blackboard-pane")).toBeVisible()}
});
