import {expect,test} from "@playwright/test";
import {mockApi} from "./mock-api";

test("touch input and scientific keyboard share the mobile MathLive field",async({browser})=>{
 const context=await browser.newContext({viewport:{width:412,height:915},screen:{width:412,height:915},deviceScaleFactor:2.625,isMobile:true,hasTouch:true});const page=await context.newPage();await mockApi(page);await page.goto("/");
 const field=page.locator("math-field[aria-label='Tableau de résolution']");await expect(field).toBeVisible();await field.tap();
 await expect.poll(()=>field.evaluate(element=>element.shadowRoot?.querySelector("[part=keyboard-sink]")?.getAttribute("inputmode"))).toBe("text");
 await expect.poll(()=>field.evaluate(element=>element.shadowRoot?.activeElement?.getAttribute("part"))).toBe("keyboard-sink");
 await page.keyboard.type("Soit f(x)=x");await expect.poll(()=>field.evaluate(element=>(element as HTMLElement&{value:string}).value)).toContain("Soit");
 const before=await field.evaluate(element=>({value:(element as HTMLElement&{value:string}).value,position:(element as HTMLElement&{position:number}).position}));const scientific=page.getByRole("button",{name:"Clavier scientifique"});await scientific.tap();await expect(scientific).toHaveAttribute("aria-expanded","true");
 await expect.poll(()=>field.evaluate(element=>element.shadowRoot?.querySelector("[part=keyboard-sink]")?.getAttribute("inputmode"))).toBe("none");expect(await field.evaluate(element=>({value:(element as HTMLElement&{value:string}).value,position:(element as HTMLElement&{position:number}).position}))).toEqual(before);
 await scientific.tap();await expect(scientific).toHaveAttribute("aria-expanded","false");await field.tap();await expect.poll(()=>field.evaluate(element=>element.shadowRoot?.querySelector("[part=keyboard-sink]")?.getAttribute("inputmode"))).toBe("text");await expect.poll(()=>field.evaluate(element=>element.shadowRoot?.activeElement?.getAttribute("part"))).toBe("keyboard-sink");
 await page.keyboard.type(" donc");await page.keyboard.press("Enter");await page.keyboard.type("f(x)=x+1");await expect.poll(()=>field.evaluate(element=>(element as HTMLElement&{value:string}).value)).toContain("f(x)");await expect(page.locator(".save")).toContainText(/Enregistré|Sauvegarde/,{timeout:5000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth)).toBe(true);await context.close();
});
