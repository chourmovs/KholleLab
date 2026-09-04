"use client";
import {useState} from "react";
import type {ProblemDetail} from "@/lib/types";
import {DifficultyBadge} from "./difficulty-badge";
import {TopicBadge} from "./topic-badge";
import {SourceBadge} from "./source-badge";
import {MathContent} from "./math-content";

type ResourceKind = "course" | "video";

function recordConsultation(problemId:string, kind:ResourceKind) {
  const key=`khollelab.resources.${problemId}`;
  try {
    const current=JSON.parse(localStorage.getItem(key) ?? "{}") as Record<string,number>;
    current[kind]=(current[kind] ?? 0)+1;
    localStorage.setItem(key,JSON.stringify(current));
  } catch { /* Analytics must never block access to curated help. */ }
}

export function ProblemPanel({problem}:{problem:ProblemDetail}) {
  const [open,setOpen]=useState<ResourceKind>();
  const course=problem.resources?.course_points[0];
  const video=problem.resources?.videos[0];
  function show(kind:ResourceKind) { recordConsultation(problem.id,kind); setOpen(kind); }
  return <section className="panel problem">
    <div className="eyebrow">Énoncé</div><h1>{problem.title}</h1>
    {problem.subtitle&&<p>{problem.subtitle}</p>}
    <div className="problem-meta"><span className="badge">{problem.level.replace("premiere","Première").replace("terminale","Terminale")}</span><DifficultyBadge difficulty={problem.difficulty}/>{problem.estimatedMinutes&&<span className="badge">~{problem.estimatedMinutes} min</span>}</div>
    <div className="topics">{problem.topics.map(topic=><TopicBadge key={topic} topic={topic}/>)}</div>
    <SourceBadge source={problem.source} year={problem.year}/><MathContent content={problem.statement}/>
    {(course||video)&&<div className="resource-actions" aria-label="Ressources pédagogiques">{course&&<button onClick={()=>show("course")}>📘 Point de cours</button>}{video&&<button onClick={()=>show("video")}>▶ Vidéo{video.duration_minutes?` ${video.duration_minutes} min`:""}</button>}</div>}
    {open==="course"&&course&&<div className="resource-modal" role="dialog" aria-modal="true" aria-label="Point de cours"><button className="resource-close" aria-label="Fermer" onClick={()=>setOpen(undefined)}>×</button><div className="eyebrow">Point de cours</div><h2>{course.title}</h2><MathContent content={course.summary}/></div>}
    {open==="video"&&video&&<div className="resource-modal video-resource" role="dialog" aria-modal="true" aria-label="Vidéo"><button className="resource-close" aria-label="Fermer" onClick={()=>setOpen(undefined)}>×</button><div className="eyebrow">Vidéo</div><h2>▶ {video.title}</h2><p>{[video.author,video.duration_minutes&&`${video.duration_minutes} min`].filter(Boolean).join(" · ")}</p><a href={video.url} target="_blank" rel="noopener noreferrer">Voir la vidéo</a></div>}
  </section>
}
