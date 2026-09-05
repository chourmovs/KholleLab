"use client";
import {useEffect,useState} from "react";
import {getProblemResources} from "@/lib/api";
import type {PedagogicalResource,ProblemDetail,ResourceType} from "@/lib/types";
import {DifficultyBadge} from "./difficulty-badge";
import {TopicBadge} from "./topic-badge";
import {SourceBadge} from "./source-badge";
import {MathContent} from "./math-content";
import {PedagogicalResourceDialog} from "./pedagogical-resource-dialog";

export function CollapsibleProblemPanel({problem}:{problem:ProblemDetail}) {
  const[selected,setSelected]=useState<string>(),[expanded,setExpanded]=useState(true),[loaded,setLoaded]=useState<{problemId:string;resources:PedagogicalResource[]}>();
  const resources=loaded?.problemId===problem.id?loaded.resources:[];
  useEffect(()=>{let active=true;getProblemResources(problem.id).then(value=>{if(active)setLoaded({problemId:problem.id,resources:value.resources})}).catch(()=>{if(active)setLoaded({problemId:problem.id,resources:[]})});return()=>{active=false}},[problem.id]);
  const first=(type:ResourceType)=>resources.find(resource=>resource.type===type);
  function show(resource:PedagogicalResource){try{const key=`khollelab.resources.${problem.id}`,current=JSON.parse(localStorage.getItem(key)??"{}") as Record<string,number>;current[resource.type]=(current[resource.type]??0)+1;localStorage.setItem(key,JSON.stringify(current))}catch{}setSelected(resource.id)}
  return <section className="panel problem collapsible-problem"><button className="problem-toggle" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}><span>{expanded?"▾":"▸"} ÉNONCÉ</span><strong>{problem.title}</strong><span>Niveau {problem.curriculum.level==="premiere"?"Première":problem.curriculum.level} · Difficulté {problem.curriculum.difficulty} · {problem.topics[0]}{problem.estimatedMinutes?` · ~${problem.estimatedMinutes} min`:""}</span></button>{expanded&&<div className="problem-body">{problem.subtitle&&<p>{problem.subtitle}</p>}<div className="problem-meta"><span className="badge">Niveau : {problem.curriculum.level}</span><DifficultyBadge difficulty={problem.curriculum.difficulty}/>{problem.estimatedMinutes&&<span className="badge">~{problem.estimatedMinutes} min</span>}</div><div className="topics">{problem.topics.map(topic=><TopicBadge key={topic} topic={topic}/>)}</div><SourceBadge source={problem.source} year={problem.year}/><MathContent content={problem.statement}/>{!!problem.prerequisites.length&&<details className="prerequisites"><summary>Prérequis</summary><p>Prérequis conseillés :</p><ul>{problem.prerequisites.map(item=><li key={item}>{item.replaceAll("-"," ")}</li>)}</ul></details>}{resources.length>0&&<div className="resource-actions" aria-label="Ressources pédagogiques">{first("course")&&<button onClick={()=>show(first("course")!)}>📘 Point de cours</button>}{first("example")&&<button onClick={()=>show(first("example")!)}>Exemple guidé</button>}{first("video")&&<button onClick={()=>show(first("video")!)}>▶ Vidéo</button>}</div>}{selected&&<PedagogicalResourceDialog key={selected} resourceId={selected} onClose={()=>setSelected(undefined)}/>}</div>}</section>
}
export const ProblemPanel=CollapsibleProblemPanel;
