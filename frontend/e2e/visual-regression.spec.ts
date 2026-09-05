import {expect,test} from "@playwright/test";

const viewports=[{name:"desktop",width:1440,height:900},{name:"compact",width:1024,height:900},{name:"mobile",width:390,height:844}];
for(const viewport of viewports)test(`visual regression — ${viewport.width}x${viewport.height}`,async({page})=>{
  await page.setViewportSize(viewport);
  await page.goto("/");
  await page.locator("main").waitFor();
  await expect(page).toHaveScreenshot(`workspace-${viewport.name}.png`,{animations:"disabled",fullPage:true});
});
