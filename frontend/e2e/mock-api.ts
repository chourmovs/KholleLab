import type {Page} from "@playwright/test";

const problem={id:"e2e-problem",title:"Functions",curriculum:{level:"seconde",difficulty:2,expectations:["seconde-functions"]},topics:["algebra"],source:{type:"internal",name:"Playwright"},statement:"Pour $f(x)=-2x+7$, déterminer l’antécédent de $1$.",hint_levels:[],prerequisites:[],skills:[]};
const attempt={id:"00000000-0000-4000-8000-000000000001",problem_id:problem.id,status:"draft",solution_markdown:"",revision:0,elapsed_seconds:0,started_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z",submitted_at:null};

export async function mockApi(page:Page){
  let savedAttempt={...attempt};
  await page.route("**/api/**",async route=>{
    const path=new URL(route.request().url()).pathname;
    let body:unknown;
    if(path==="/api/curriculum")body={academic_year:"2026-2027",levels:[
      {id:"quatrieme",label:"Quatrième",short_label:"4e",stage:"college",programme:{id:"cycle4",label:"Cycle 4"},domains:[]},
      {id:"troisieme",label:"Troisième",short_label:"3e",stage:"college",programme:{id:"cycle4",label:"Cycle 4"},domains:[]},
      {id:"seconde",label:"Seconde",short_label:"2de",stage:"lycee",programme:{id:"seconde",label:"Seconde"},domains:[{id:"functions",label:"Fonctions",expectations:[{id:"seconde-functions",label:"Étudier des fonctions"}]}]},
      {id:"premiere",label:"Première",short_label:"1re",stage:"lycee",programme:{id:"premiere",label:"Première"},domains:[]},
      {id:"terminale",label:"Terminale",short_label:"Tle",stage:"lycee",programme:{id:"terminale",label:"Terminale"},domains:[]},
      {id:"maths-sup",label:"Maths Sup",short_label:"Sup",stage:"cpge",programme:{id:"cpge",label:"CPGE"},domains:[]},
      {id:"maths-spe",label:"Maths Spé",short_label:"Spé",stage:"cpge",programme:{id:"cpge",label:"CPGE"},domains:[]},
    ],difficulties:[1,2,3,4,5].map(id=>({id,label:`Niveau ${id}`}))};
    else if(path==="/api/problems")body=[problem];
    else if(path==="/api/problems/select")body={problem,requested_level:"seconde",requested_difficulty:2,actual_difficulty:2,fallback_used:false};
    else if(path==="/api/sessions/active/latest")body=null;
    else if(path===`/api/problems/${problem.id}/resources`)body={problem_id:problem.id,resources:[]};
    else if(path==="/api/health")body={status:"ok",database:"ok",problem_corpus:"ok",problem_count:1,resource_corpus:"ok",resource_count:1,curriculum_levels:1};
    else if(path==="/api/inference/status")body={provider:"fake",status:"ready",family:"fake",fast_model:"fake",fast_backend:"fake",deep_model:"fake",deep_backend:"fake"};
    else if(path==="/api/sessions")body={session_id:"00000000-0000-4000-8000-000000000002",problem_id:problem.id,problem_title:problem.title,status:"active",created_at:attempt.started_at,updated_at:savedAttempt.updated_at,started_at:attempt.started_at,completed_at:null,duration_seconds:0,number_of_attempts:1,number_of_tutor_interactions:0,outcome:null,problem,attempts:[savedAttempt],current_attempt_id:savedAttempt.id,final_work:"",tutor_assessment:null,resource_recommendation:null};
    else if(path==="/api/attempts"||path===`/api/attempts/${attempt.id}`){if(route.request().method()==="PATCH"){const update=route.request().postDataJSON() as {solution_markdown:string;elapsed_seconds:number};savedAttempt={...savedAttempt,solution_markdown:update.solution_markdown,elapsed_seconds:update.elapsed_seconds,revision:savedAttempt.revision+1,updated_at:new Date().toISOString()}}body=savedAttempt}
    else{await route.fulfill({status:404,json:{detail:"Not found"}});return}
    await route.fulfill({json:body});
  });
}
