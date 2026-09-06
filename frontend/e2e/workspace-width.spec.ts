import {expect,test} from "@playwright/test";
import {mockApi} from "./mock-api";

const viewports=[{width:1440,height:900},{width:1366,height:768},{width:1024,height:768},{width:768,height:1024},{width:390,height:844},{width:360,height:800}];
for(const viewport of viewports)test(`workspace remains structured at ${viewport.width}px`,async({page})=>{
  await mockApi(page);await page.setViewportSize(viewport);await page.goto("/");
  const main=page.locator("main");await expect(main).toBeVisible();
  const box=await main.boundingBox();expect(box).not.toBeNull();expect(box!.width).toBeLessThanOrEqual(1722);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth)).toBe(true);
  await expect(page.getByRole("navigation",{name:"Outils du tableau"})).toBeVisible();
  await expect(page.locator(".professor-pane")).toBeVisible();
  const geometry=await page.evaluate(()=>{
    const box=(selector:string)=>document.querySelector(selector)!.getBoundingClientRect();
    const contains=(outer:DOMRect,inner:DOMRect)=>inner.left>=outer.left-.5&&inner.right<=outer.right+.5&&inner.top>=outer.top-.5&&inner.bottom<=outer.bottom+.5;
    const intersects=(a:DOMRect,b:DOMRect)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
    const header=box(".app-header"),logo=box(".brand-lockup"),utilities=box(".header-utilities"),professor=box(".professor-pane"),portrait=box(".professor-portrait"),navigation=box(".problem-navigation"),workspace=box(".workspace-layout"),tools=box(".tool-rail");
    return {logoContained:contains(header,logo),logoUtilitiesOverlap:intersects(logo,utilities),portraitContained:contains(professor,portrait),navigationPortraitOverlap:intersects(navigation,portrait),toolsContained:contains(workspace,tools)};
  });
  if(viewport.width>700){expect(geometry.logoContained).toBe(true);expect(geometry.logoUtilitiesOverlap).toBe(false)}
  expect(geometry.portraitContained).toBe(true);expect(geometry.navigationPortraitOverlap).toBe(false);expect(geometry.toolsContained).toBe(true);
  if(viewport.width>=1200){
    const board=await page.locator(".blackboard-pane").boundingBox();
    const statement=await page.locator(".statement-pane").boundingBox();
    const professor=await page.locator(".professor-pane").boundingBox();
    expect(board!.width).toBeGreaterThan(statement!.width);expect(board!.width).toBeGreaterThan(professor!.width);
    expect(statement!.width).toBeGreaterThanOrEqual(389);
    expect(board!.width).toBeGreaterThanOrEqual(450);
    expect(professor!.width).toBeGreaterThanOrEqual(285);
    const styles=await page.evaluate(()=>{
      const problem=getComputedStyle(document.querySelector(".problem-body")!);
      const portrait=getComputedStyle(document.querySelector(".professor-portrait")!);
      const image=getComputedStyle(document.querySelector(".professor-portrait img")!);
      return {problemBackgroundImage:problem.backgroundImage,portraitOverflow:portrait.overflow,imageObjectFit:image.objectFit};
    });
    expect(styles.problemBackgroundImage).toBe("none");
    expect(styles.portraitOverflow).toBe("hidden");
    expect(styles.imageObjectFit).toBe("cover");
  }
});

test("l’énoncé compact se replie sans masquer l’espace de travail",async({page})=>{
  await mockApi(page);await page.goto("/");const toggle=page.locator(".problem-toggle");
  if(await toggle.count()){await expect(toggle).toHaveAttribute("aria-expanded","true");await toggle.click();await expect(toggle).toHaveAttribute("aria-expanded","false");await expect(page.locator(".blackboard-pane")).toBeVisible()}
});
