"use client";
import {useEffect,useState} from "react";
import Image from "next/image";
import {Activity,FileText,RefreshCw} from "lucide-react";
import {StatusBadge} from "./status-badge";
import {DiagnosticsModal} from "./diagnostics-modal";
import type {HealthStatus,InferenceStatus} from "@/lib/api";

const labels:Record<string,string>={ready:"IA ● prête",unavailable:"IA ⚠ indisponible",error:"IA en erreur",disabled:"IA désactivée"};
const title=(v?:InferenceStatus)=>v?`Hugging Face Inference Providers\nFamille : ${v.family}\nFAST : ${v.fast_model} · ${v.fast_backend}\nDEEP : ${v.deep_model} · ${v.deep_backend}`:"Diagnostic en attente";
export function AppHeader({health,inference,onRefresh}:{health?:HealthStatus|null;inference?:InferenceStatus;onRefresh:()=>void}){
  const[logs,setLogs]=useState(false);
  useEffect(()=>{const open=()=>setLogs(true);window.addEventListener("khollelab:open-diagnostics",open);return()=>window.removeEventListener("khollelab:open-diagnostics",open)},[]);
  const online=health?.status==="ok"&&health.problem_corpus==="ok"&&health.problem_count>0;
  return <><header className="app-header"><div className="header-maths" aria-hidden="true"/><div className="desktop-brand"><Image src="/assets/brand/logo-horizontal.svg" alt="KholleLab — La salle de colle, autrement" width={480} height={120} priority/></div><div className="mobile-brand"><Image src="/assets/brand/app-icon-512.png" alt="" width={58} height={58}/><div><strong>KholleLab</strong><p>La salle de colle, autrement.</p></div></div><div className="header-utilities"><details className="inference-status"><summary className="status-badge success" title={title(inference)}><Activity/>{inference?.provider==="fake"?"IA simulée":labels[inference?.status??"unavailable"]}</summary><div className="inference-popover"><span style={{whiteSpace:"pre-line"}}>{title(inference)}</span><button onClick={onRefresh}><RefreshCw/> Actualiser</button></div></details><button className="utility-button" title="Logs et diagnostics" aria-label="Ouvrir les logs et diagnostics" onClick={()=>setLogs(true)}><FileText/><span>Logs</span></button><span className="session-pill">Session 001</span><StatusBadge online={online}/></div></header>{logs&&<DiagnosticsModal onClose={()=>setLogs(false)}/>}</>;
}
