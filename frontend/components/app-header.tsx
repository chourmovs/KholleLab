"use client";
import {useEffect,useRef,useState} from "react";
import Image from "next/image";
import Link from "next/link";
import {Activity,FileText,History,RefreshCw,UserRound} from "lucide-react";
import {StatusBadge} from "./status-badge";
import {DiagnosticsModal} from "./diagnostics-modal";
import type {HealthStatus,InferenceStatus,Account} from "@/lib/api";
import type {ProgressionSummary} from "@/lib/types";
import {getCurrentAccount,getProgression,logoutAccount} from "@/lib/api";
import {AccountDialog} from "./account-dialog";

const labels:Record<string,string>={ready:"IA ● prête",unavailable:"IA ⚠ indisponible",error:"IA en erreur",disabled:"IA désactivée"};
const title=(v?:InferenceStatus)=>v?`Hugging Face Inference Providers\nFamille : ${v.family}\nFAST : ${v.fast_model} · ${v.fast_backend}\nDEEP : ${v.deep_model} · ${v.deep_backend}`:"Diagnostic en attente";
export function AppHeader({health,inference,onRefresh,onHistory,onProfile}:{health?:HealthStatus|null;inference?:InferenceStatus;onRefresh:()=>void;onHistory?:()=>void;onProfile?:()=>void}){
  const[logs,setLogs]=useState(false);
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
  useEffect(()=>{const open=()=>setLogs(true);window.addEventListener("khollelab:open-diagnostics",open);return()=>window.removeEventListener("khollelab:open-diagnostics",open)},[]);
  const online=health?.status==="ok"&&health.problem_corpus==="ok"&&health.problem_count>0;
  return <><header className="app-header"><div className="header-maths" aria-hidden="true"/><div className="brand-lockup"><Image src="/assets/brand/khollelab-logo-dark.svg" alt="KHOLLELAB" width={500} height={125} style={{height:"auto"}} priority/></div><div className="header-utilities"><Link className="utility-button workspace-home" href="/">Accueil</Link><details className="inference-status"><summary className="status-badge success" title={title(inference)}><Activity/>{inference?.provider==="fake"?"IA simulée":labels[inference?.status??"unavailable"]}</summary><div className="inference-popover"><span style={{whiteSpace:"pre-line"}}>{title(inference)}</span><button onClick={onRefresh}><RefreshCw/> Actualiser</button></div></details><button className="utility-button" title="Historique" onClick={onHistory}><History/><span>Historique</span></button><button className="utility-button" title={account.authenticated?"Mon compte":"Se connecter"} onClick={()=>setAccountOpen(true)}><UserRound/><span>{account.authenticated?(account.display_name||account.email?.split("@")[0]||"Mon compte"):"Se connecter"}</span></button><button className="utility-button" title="Profil" aria-label="Profil d’apprentissage" onClick={onProfile}><UserRound/><span>Profil</span></button><button className="utility-button" title="Logs et diagnostics" aria-label="Ouvrir les logs et diagnostics" onClick={()=>setLogs(true)}><FileText/><span>Logs</span></button>{progression&&<button type="button" className="progression-pill" onClick={onProfile} aria-label={`Progression : grade ${progression.grade}, ${progression.total_xp} XP, série de ${progression.current_streak_days} jours. Ouvrir le profil.`}><span className="progression-grade">G{progression.grade} · </span>{progression.total_xp} XP · 🔥{progression.current_streak_days}</button>}<StatusBadge online={online}/></div></header>{toast&&<div className="xp-toast" role="status" aria-live="polite">{toast}</div>}{logs&&<DiagnosticsModal onClose={()=>setLogs(false)}/>} {accountOpen&&<AccountDialog account={account} onAccount={value=>{setAccount(value);void refreshProgression()}} onClose={()=>setAccountOpen(false)}/>} {account.authenticated&&<button className="account-logout" onClick={async()=>{await logoutAccount();setAccount({authenticated:false,anonymous_sessions_available:0});await refreshProgression()}}>Se déconnecter</button>}</>;
}
