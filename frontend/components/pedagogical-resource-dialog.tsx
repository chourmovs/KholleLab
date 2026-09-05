"use client";
import {useEffect,useState} from "react";
import {getResource} from "@/lib/api";
import type {PedagogicalResource} from "@/lib/types";
import {MathContent} from "./math-content";

export function PedagogicalResourceDialog({resourceId,onClose}:{resourceId:string;onClose:()=>void}){
  const[resource,setResource]=useState<PedagogicalResource>(),[failed,setFailed]=useState(false),[solution,setSolution]=useState(false);
  useEffect(()=>{let active=true;getResource(resourceId).then(value=>{if(active)setResource(value)}).catch(()=>{if(active)setFailed(true)});return()=>{active=false}},[resourceId]);
  const label=resource?.type==="course"?"RAPPEL DE COURS":resource?.type==="example"?"EXEMPLE GUIDÉ":"RESSOURCE VIDÉO";
  return <div className="resource-modal" role="dialog" aria-modal="true" aria-label={label}><button className="resource-close" aria-label="Fermer" onClick={onClose}>×</button>{failed?<p role="alert">Cette ressource n’est pas disponible pour le moment.</p>:!resource?<p>Chargement de la ressource…</p>:<><div className="eyebrow">{label}</div><h2>{resource.title}</h2>{resource.type==="course"&&<><p>{resource.summary}</p><MathContent content={resource.content}/></>}{resource.type==="example"&&<><p className="example-notice">Exemple distinct de l’exercice en cours.</p><MathContent content={resource.statement}/><button className="example-solution-toggle" onClick={()=>setSolution(value=>!value)}>{solution?"Masquer la solution de l’exemple":"Voir la solution de l’exemple"}</button>{solution&&<div className="example-solution"><MathContent content={resource.solution}/></div>}</>}{resource.type==="video"&&<><p>{resource.author} · {resource.duration_minutes} min</p><a href={resource.url} target="_blank" rel="noopener noreferrer">Voir la vidéo</a></>}</>}</div>
}
