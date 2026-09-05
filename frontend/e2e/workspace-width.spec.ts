import {expect,test} from "@playwright/test";

const viewports=[{width:1366,height:768},{width:1440,height:900},{width:1920,height:1080},{width:2560,height:1440},{width:3840,height:2160},{width:390,height:844}];
for(const viewport of viewports)test(`workspace occupies 90vw at ${viewport.width}x${viewport.height}`,async({page})=>{
  await page.setViewportSize(viewport); await page.goto("/");
  const workspace=page.locator("main"); await expect(workspace).toBeVisible();
  const box=await workspace.boundingBox(); expect(box).not.toBeNull();
  const ratio=box!.width/viewport.width; expect(ratio).toBeGreaterThanOrEqual(.88); expect(ratio).toBeLessThanOrEqual(.92);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width+2);
  if(viewport.width>=1366){
    const board=await page.locator(".blackboard-pane").boundingBox(); const statement=await page.locator(".statement-pane").boundingBox();
    expect(board!.width).toBeGreaterThan(statement!.width); expect(board!.width/box!.width).toBeGreaterThan(.6);
  }
  if(viewport.width===2560)expect(box!.width).toBeGreaterThan(2200);
  if(viewport.width===3840){expect(box!.width).toBeGreaterThan(3300); const statement=await page.locator(".statement-pane").boundingBox(); expect(statement!.width/box!.width).toBeLessThan(.25)}
});
