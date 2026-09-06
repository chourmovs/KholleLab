import {expect,test} from "@playwright/test";
import {mockApi} from "./mock-api";

test("Autre exercice sends explicit adaptive intent",async({page})=>{
  await mockApi(page);
  const adaptive=page.waitForRequest(request=>{
    const url=new URL(request.url());
    return url.pathname==="/api/problems/select"&&url.searchParams.get("mode")==="adaptive";
  });
  await page.goto("/");
  await expect(page.getByText("Functions")).toBeVisible();
  await page.getByRole("button",{name:"Choisir un autre exercice"}).click();
  await adaptive;
  await expect(page.getByText("Functions")).toBeVisible();
});
