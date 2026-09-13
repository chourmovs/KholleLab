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

describe("selectProblem",()=>{
  it("sends curriculum domain separately from the legacy topic filter",async()=>{
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({problem:null,requested_level:"seconde",requested_difficulty:2,fallback_used:false})));
    vi.stubGlobal("fetch",fetch);
    const {selectProblem}=await import("./api");
    await selectProblem({level:"seconde",difficulty:2,domain:"algebra",expectation:"lycee-2026-2de-algebra"});
    expect(fetch.mock.calls[0][0]).toContain("domain=algebra");
    expect(fetch.mock.calls[0][0]).toContain("expectation=lycee-2026-2de-algebra");
    expect(fetch.mock.calls[0][0]).not.toContain("topic=algebra");
  });
});

describe("guided curriculum contracts",()=>{
  afterEach(()=>vi.unstubAllGlobals());
  it("gets the guided problem without client-owned selection filters",async()=>{
    const wire={problem:{id:"p1",title:"P",curriculum:{level:"seconde",difficulty:2,expectations:[]},topics:[],source:{type:"original",name:"test"},statement:"S",hint_levels:[1],prerequisites:[],skills:[]},current_level:"seconde",target_difficulty:2,actual_difficulty:2,candidate_pool:"unsolved",selection_mode:"guided",level_progress:{eligible:1,solved:0,progress:0,progress_percent:0}};
    const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify(wire)));vi.stubGlobal("fetch",fetch);
    const {getNextProblem}=await import("./api");
    await expect(getNextProblem()).resolves.toMatchObject({problem:{id:"p1",hintLevels:[1]},candidate_pool:"unsolved"});
    expect(fetch.mock.calls[0][0]).toBe("/api/problems/next");
  });
  it("uses PR12 curriculum progress endpoints",async()=>{
    const payload={initial_level:"seconde",current_level:"seconde",highest_unlocked_level:"seconde",onboarding_completed:true,unlock_ratio:.6,levels:[]};
    const fetch=vi.fn().mockImplementation(()=>Promise.resolve(new Response(JSON.stringify(payload))));vi.stubGlobal("fetch",fetch);
    const {getCurriculumProgress,setInitialCurriculumLevel,setCurrentCurriculumLevel}=await import("./api");
    await getCurriculumProgress();await setInitialCurriculumLevel("seconde");await setCurrentCurriculumLevel("seconde");
    expect(fetch.mock.calls.map(call=>call[0])).toEqual(["/api/curriculum-progress","/api/curriculum-progress/initial-level","/api/curriculum-progress/current-level"]);
    expect(fetch.mock.calls[1][1]).toMatchObject({method:"PUT"});
  });
});
