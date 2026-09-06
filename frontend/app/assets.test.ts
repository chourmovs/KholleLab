import {existsSync} from "node:fs";
import {join} from "node:path";
import {describe,expect,it} from "vitest";

const required=["brand/khollelab-logo-dark.svg","brand/khollelab-logo-light.svg","brand/khollelab-mark.svg","brand/favicon.ico","brand/khollelab-icon-32.png","brand/apple-touch-icon.png","brand/khollelab-icon-192.png","brand/khollelab-icon-512.png","backgrounds/chalkboard-bg.jpg","backgrounds/classroom-bg.jpg","illustrations/professor-euler-hero.png","illustrations/professor-euler-card.png","illustrations/professor-placeholder.svg","illustrations/professor-placeholder.png","shapes/wave-divider.svg","icons/lightbulb.svg","icons/life-buoy.svg","icons/bell-off.svg","patterns/formula-pattern.svg"];
describe("KHOLLELAB visual identity asset pack",()=>{it.each(required)("ships /assets/%s",asset=>{expect(existsSync(join(process.cwd(),"public/assets",asset))).toBe(true)})});
