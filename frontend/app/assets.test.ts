import {existsSync,readFileSync} from "node:fs";
import {join} from "node:path";
import {describe,expect,it} from "vitest";

const required=["brand/khollelab-logo-dark.svg","brand/khollelab-logo-light.svg","brand/khollelab-mark.svg","brand/favicon.ico","brand/khollelab-icon-32.png","brand/apple-touch-icon.png","brand/khollelab-icon-192.png","brand/khollelab-icon-512.png","backgrounds/chalkboard-bg.jpg","backgrounds/classroom-bg.jpg","illustrations/professor-euler-hero.png","illustrations/professor-euler-card.png","illustrations/professor-placeholder.svg","illustrations/professor-placeholder.png","shapes/wave-divider.svg","icons/lightbulb.svg","icons/life-buoy.svg","icons/bell-off.svg","patterns/formula-pattern.svg"];
describe("KHOLLELAB visual identity asset pack",()=>{it.each(required)("ships /assets/%s",asset=>{expect(existsSync(join(process.cwd(),"public/assets",asset))).toBe(true)})});

describe("web app manifest",()=>{it("is available with the installable KHOLLELAB configuration",()=>{const manifest=JSON.parse(readFileSync(join(process.cwd(),"public/manifest.webmanifest"),"utf8"));expect(manifest).toMatchObject({name:"KHOLLELAB",short_name:"KHOLLELAB",id:"/",start_url:"/",scope:"/",display:"standalone",theme_color:"#10271E",background_color:"#10271E",icons:[{src:"/assets/brand/khollelab-icon-192.png",sizes:"192x192",type:"image/png"},{src:"/assets/brand/khollelab-icon-512.png",sizes:"512x512",type:"image/png"}]})})});
