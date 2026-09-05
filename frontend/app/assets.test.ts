import {existsSync} from "node:fs";
import {join} from "node:path";
import {describe,expect,it} from "vitest";

const required=["brand/header-banner.svg","backgrounds/chalkboard-bg.jpg","backgrounds/classroom-bg.jpg","illustrations/professor-illustration.svg","shapes/wave-divider.svg","icons/lightbulb.svg","icons/life-buoy.svg","icons/bell-off.svg","patterns/formula-pattern.svg"];
describe("classic academic asset pack",()=>{it.each(required)("ships /assets/%s",asset=>{expect(existsSync(join(process.cwd(),"public/assets",asset))).toBe(true)})});
