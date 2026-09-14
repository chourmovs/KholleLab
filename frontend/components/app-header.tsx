"use client";
import {useEffect,useRef,useState} from "react";
import Image from "next/image";
import Link from "next/link";
import {Activity,History,RefreshCw,UserRound} from "lucide-react";
import {DiagnosticsModal} from "./diagnostics-modal";
import type {HealthStatus,InferenceStatus,Account} from "@/lib/api";
import type {ProgressionSummary} from "@/lib/types";
import {getCurrentAccount,getProgression,logoutAccount} from "@/lib/api";
import {AccountDialog} from "./account-dialog";

type ServiceState={apiReady:boolean;corpusReady:boolean;inferenceReady:boolean;degraded:boolean;label:string};

function serviceState(health?:HealthStatus|null,inference?:InferenceStatus):ServiceState{
  const apiReady=health?.status==="ok";
  const corpusReady=apiReady&&health.problem_corpus==="ok"&&health.problem_count>0;
  const inferenceReady=inference?.status==="ready";
  const apiUnavailable=health===null;
  const inferenceUnavailable=Boolean(inference)&&!inferenceReady;
  const degraded=apiUnavailable||inferenceUnavailable||(Boolean(health)&&!corpusReady);
  let label="Services en vérification";
  if(apiReady&&corpusReady&&inferenceReady)label="Services OK";
  else if(apiUnavailable&&inferenceUnavailable)label="Services dégradés";
  else if(apiUnavailable)label="API indisponible";
  else if(inferenceUnavailable)label="IA indisponible";
  else if(health&&!corpusReady)label="Services dégradés";
  return{apiReady,corpusReady,inferenceReady,degraded,label};
}

function inferenceSummary(inference?:InferenceStatus){
  if(!inference)return "Modèle : vérification en cours";
  return `Modèle : ${inference.family} · ${inference.provider}\nFAST : ${inference.fast_model} · ${inference.fast_backend}\nDEEP : ${inference.deep_model} · ${inference.deep_backend}`;
}

export function AppHeader({health,inference,onRefresh,onHistory,onProfile}:{health?:HealthStatus|null;inference?:InferenceStatus;onRefresh:()=>void;onHistory?:()=>void;onProfile?:()=>void}){
  const[diagnosticsOpen,setDiagnosticsOpen]=useState(false);
  const[account,setAccount]=useState<Account>({authenticated:false,anonymous_sessions_available:0});
  const[accountOpen,setAccountOpen]=useState(false);
  const[progression,setProgression]=useState<ProgressionSummary>();
  const[toast,setToast]=useState<string>();
  const progressionRef=useRef<ProgressionSummary|undefined>(undefined);
  const toastTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  async function refreshProgression(reason?:string){
    try{
      const next=await getProgression();
      const previous=progressionRef.current;
      progressionRef.current=next;
      setProgression(next);
      if(reason==="submission"&&previous&&next.total_xp>previous.total_xp){
        setToast(`+${next.total_xp-previous.total_xp} XP`);
        if(toastTimer.current)clearTimeout(toastTimer.current);
        toastTimer.current=setTimeout(()=>setToast(undefined),2000);
      }
    }catch{/* Keep the workspace usable if this summary is unavailable. */}
  }
  useEffect(()=>{void Promise.resolve(getCurrentAccount()).then(value=>value&&setAccount(value)).catch(()=>undefined)},[]);
  useEffect(()=>{
    queueMicrotask(()=>void refreshProgression());
    const refresh=(event:Event)=>void refreshProgression((event as CustomEvent<{reason?:string}>).detail?.reason);
    window.addEventListener("khollelab:progression-refresh",refresh);
    return()=>{window.removeEventListener("khollelab:progression-refresh",refresh);if(toastTimer.current)clearTimeout(toastTimer.current)};
  },[]);
  useEffect(()=>{const open=()=>setDiagnosticsOpen(true);window.addEventListener("khollelab:open-diagnostics",open);return()=>window.removeEventListener("khollelab:open-diagnostics",open)},[]);
  const services=serviceState(health,inference);
  const accountLabel=account.authenticated?(account.display_name||account.email?.split("@")[0]||"Mon compte"):"Se connecter";
  return <>
    <header className="app-header">
      <div className="header-maths" aria-hidden="true"/>
      <div className="brand-lockup"><Image src="/assets/brand/khollelab-logo-dark.svg" alt="KHOLLELAB" width={500} height={125} style={{width:"auto",height:"auto"}} priority/></div>
      <div className="header-utilities">
        <Link className="utility-button workspace-home" href="/">Accueil</Link>
        <button className="utility-button" title="Historique" onClick={onHistory}><History/><span>Historique</span></button>
        {progression&&<button type="button" className="progression-pill" onClick={onProfile} aria-label={`Rang XP ${progression.xp_rank}, ${progression.total_xp} XP, série de ${progression.current_streak_days} jours. Ouvrir le profil d’apprentissage.`}><span>R{progression.xp_rank}</span><span className="progression-xp"> · {progression.total_xp} XP</span><span className="progression-streak"> · 🔥{progression.current_streak_days}</span></button>}
        <button className="utility-button account-control" title={account.authenticated?"Mon compte":"Se connecter"} aria-label={account.authenticated?`${accountLabel} — Mon compte`:"Se connecter"} onClick={()=>setAccountOpen(true)}><UserRound/><span>{accountLabel}</span></button>
        <details className="service-status">
          <summary className={`status-badge ${services.degraded?"warning":services.label==="Services OK"?"success":""}`} aria-label={`État du système : ${services.label}`}><Activity aria-hidden="true"/><span>{services.label}</span></summary>
          <div className="service-popover">
            <strong>État des services</strong>
            <dl><div><dt>API</dt><dd>{services.apiReady?"en ligne":"indisponible"}</dd></div><div><dt>Corpus</dt><dd>{services.corpusReady?"disponible":"indisponible"}</dd></div><div><dt>IA</dt><dd>{services.inferenceReady?"prête":"indisponible"}</dd></div></dl>
            <p className="service-model">{inferenceSummary(inference)}</p>
            <div className="service-actions"><button onClick={onRefresh}><RefreshCw/> Actualiser</button>{services.degraded&&<button onClick={()=>setDiagnosticsOpen(true)}>Diagnostic</button>}</div>
          </div>
        </details>
      </div>
    </header>
    {toast&&<div className="xp-toast" role="status" aria-live="polite">{toast}</div>}
    {diagnosticsOpen&&<DiagnosticsModal onClose={()=>setDiagnosticsOpen(false)}/>}
    {accountOpen&&<AccountDialog account={account} onAccount={value=>{setAccount(value);void refreshProgression()}} onClose={()=>setAccountOpen(false)}/>}
    {account.authenticated&&<button className="account-logout" onClick={async()=>{await logoutAccount();setAccount({authenticated:false,anonymous_sessions_available:0});await refreshProgression()}}>Se déconnecter</button>}
  </>;
}
