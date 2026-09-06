import type {Page} from "@playwright/test";

const problem={id:"e2e-problem",title:"Exercice de test",curriculum:{level:"seconde",difficulty:2},topics:["algebra"],source:{type:"internal",name:"Playwright"},statement:"Résoudre \\(x+1=2\\).",hint_levels:[],prerequisites:[],skills:[]};
const attempt={id:"00000000-0000-4000-8000-000000000001",problem_id:problem.id,status:"draft",solution_markdown:"",revision:0,elapsed_seconds:0,started_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z",submitted_at:null};

export async function mockApi(page:Page){
  await page.route("**/api/**",async route=>{
    const path=new URL(route.request().url()).pathname;
    let body:unknown;
    if(path==="/api/curriculum")body={levels:[{id:"seconde",label:"Seconde"}],difficulties:[1,2,3,4,5].map(id=>({id,label:`Niveau ${id}`}))};
    else if(path==="/api/problems")body=[problem];
    else if(path==="/api/problems/select")body={problem,requested_level:"seconde",requested_difficulty:2,actual_difficulty:2,fallback_used:false};
    else if(path===`/api/problems/${problem.id}/resources`)body={problem_id:problem.id,resources:[]};
    else if(path==="/api/health")body={status:"ok",database:"ok",problem_corpus:"ok",problem_count:1,resource_corpus:"ok",resource_count:1,curriculum_levels:1};
    else if(path==="/api/inference/status")body={provider:"fake",status:"ready",family:"fake",fast_model:"fake",fast_backend:"fake",deep_model:"fake",deep_backend:"fake"};
    else if(path==="/api/attempts"||path===`/api/attempts/${attempt.id}`)body=attempt;
    else{await route.fulfill({status:404,json:{detail:"Not found"}});return}
    await route.fulfill({json:body});
  });
}
