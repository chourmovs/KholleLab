import {expect,test} from "@playwright/test";
import {mockApi} from "./mock-api";

test("new learner chooses a curriculum before the workspace mounts",async({page})=>{
 await mockApi(page,{onboardingCompleted:false});
 await page.goto("/");
 await page.getByRole("link",{name:"Commencer"}).click();
 await expect(page).toHaveURL(/\/onboarding$/);
 await expect(page.getByRole("heading",{name:"Choisis ton niveau de départ"})).toBeVisible();
 await page.getByRole("radio",{name:/Seconde/}).click();
 await page.getByRole("button",{name:"Commencer en Seconde"}).click();
 await expect(page).toHaveURL(/\/kholle$/);
 await expect(page.locator(".blackboard-surface")).toBeVisible();
});
