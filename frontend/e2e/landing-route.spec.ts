import {expect,test} from "@playwright/test";
import {mockApi} from "./mock-api";
test("landing opens the workspace through learner intent",async({page})=>{await mockApi(page);await page.goto("/");await expect(page.getByRole("heading",{name:"Mon parcours"})).toBeVisible();await page.getByRole("link",{name:"Continuer ma khôlle"}).click();await expect(page).toHaveURL(/\/kholle$/);await expect(page.getByLabel("Tableau de rédaction")).toBeVisible()});
