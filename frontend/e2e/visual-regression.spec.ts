import {expect,test} from "@playwright/test";

const requiredAssets=["brand/khollelab-logo-dark.svg","brand/khollelab-logo-light.svg","brand/khollelab-mark.svg","brand/favicon.ico","brand/khollelab-icon-32.png","brand/apple-touch-icon.png","brand/khollelab-icon-192.png","brand/khollelab-icon-512.png","backgrounds/chalkboard-bg.jpg","backgrounds/classroom-bg.jpg","illustrations/professor-euler-hero.png","illustrations/professor-euler-card.png","illustrations/professor-placeholder.svg","illustrations/professor-placeholder.png","shapes/wave-divider.svg","icons/lightbulb.svg","icons/life-buoy.svg","icons/bell-off.svg","patterns/formula-pattern.svg"];
test("KHOLLELAB visual identity assets are served",async({request})=>{
  for(const asset of requiredAssets)expect((await request.get(`/assets/${asset}`)).status(),asset).toBe(200);
});

const viewports=[{name:"desktop",width:1440,height:900},{name:"production",width:1366,height:768},{name:"compact",width:1024,height:768},{name:"mobile",width:390,height:844}];
for(const viewport of viewports)test(`visual regression — ${viewport.width}x${viewport.height}`,async({page})=>{
  // Binary baselines live in the opt-in visual job, keeping functional CI and
  // ordinary reliability changes independent from generated image artifacts.
  test.skip(process.env.VISUAL_REGRESSION!=="1","visual baselines are not installed in functional CI");
  await page.setViewportSize(viewport);
  await page.goto("/");
  await page.locator("main").waitFor();
  await expect(page).toHaveScreenshot(`workspace-${viewport.name}.png`,{animations:"disabled",fullPage:true});
});
