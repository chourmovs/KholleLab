import {afterEach,describe,expect,it,vi} from "vitest";
import {ApiError,apiFetch} from "./api";

describe("apiFetch",()=>{
  afterEach(()=>vi.unstubAllGlobals());
  it("returns JSON and accepts an empty successful body",async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(new Response('{"ok":true}')).mockResolvedValueOnce(new Response(null,{status:204}));vi.stubGlobal("fetch",fetch);
    await expect(apiFetch<{ok:boolean}>("/ok")).resolves.toEqual({ok:true});
    await expect(apiFetch("/empty")).resolves.toBeUndefined();
  });
  it("normalizes JSON, HTML, and network errors",async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(new Response('{"error":"conflict"}',{status:409})).mockResolvedValueOnce(new Response("<h1>Bad gateway</h1>",{status:502})).mockRejectedValueOnce(new TypeError("offline"));vi.stubGlobal("fetch",fetch);
    await expect(apiFetch("/conflict")).rejects.toMatchObject({status:409,message:"conflict"});
    await expect(apiFetch("/proxy")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/offline")).rejects.toMatchObject({status:0,message:"Network request failed"});
  });
  it("turns invalid success JSON into a controlled error",async()=>{vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response("not-json")));await expect(apiFetch("/bad")).rejects.toMatchObject({status:200,message:"Invalid JSON response"})});
});
