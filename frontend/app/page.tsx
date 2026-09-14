"use client";
import {useCallback,useEffect,useState} from "react";
import Link from "next/link";
import {ArrowRight} from "lucide-react";
import {AccountDialog} from "@/components/account-dialog";
import {CurriculumProgressCard,CurriculumProgressSkeleton} from "@/components/landing/curriculum-progress-card";
import {LandingHeader} from "@/components/landing/landing-header";
import {PracticeSummary} from "@/components/landing/practice-summary";
import {RecentActivity} from "@/components/landing/recent-activity";
import {getCurrentAccount,getCurriculum,getCurriculumProgress,getProgression,getSessions,logoutAccount,type Account} from "@/lib/api";
import type {CurriculumMetadata,CurriculumProgressSummary,LearningSessionSummary,ProgressionSummary} from "@/lib/types";

type LandingData={account:Account|null;curriculum?:CurriculumMetadata;progress?:CurriculumProgressSummary;sessions:LearningSessionSummary[];progression?:ProgressionSummary;errors:Set<string>};
const emptyData:LandingData={account:null,sessions:[],errors:new Set()};
export default function LandingPage(){
 const[data,setData]=useState<LandingData>(emptyData),[loading,setLoading]=useState(true),[accountOpen,setAccountOpen]=useState(false);
 const load=useCallback(async()=>{setLoading(true);setData(emptyData);const update=<K extends keyof Omit<LandingData,"errors">>(key:K,value:LandingData[K])=>setData(current=>({...current,[key]:value}));const failed=(key:string)=>setData(current=>({...current,errors:new Set(current.errors).add(key)}));const tasks=[getCurriculumProgress().then(value=>update("progress",value)).catch(()=>failed("progress")).finally(()=>setLoading(false)),getCurrentAccount().then(value=>update("account",value)).catch(()=>failed("account")),getSessions().then(value=>update("sessions",value)).catch(()=>failed("sessions")),getProgression().then(value=>update("progression",value)).catch(()=>failed("progression")),getCurriculum().then(value=>update("curriculum",value)).catch(()=>failed("curriculum"))];await Promise.allSettled(tasks)},[]);
 useEffect(()=>{queueMicrotask(()=>void load())},[load]);
 const newLearner=!loading&&data.progress?.onboarding_completed===false;
 const active=data.sessions.some(session=>session.status==="active");
 const cta=newLearner?"Commencer":active?"Reprendre ma khôlle":"Continuer ma khôlle";
 // TODO(PR16): send non-onboarded learners to /onboarding.
 const destination="/kholle";
 return <div className="landing"><LandingHeader account={data.account} onAccount={()=>setAccountOpen(true)}/><main id="contenu" className="landing-main">{newLearner?<section className="welcome-hero" aria-labelledby="welcome-title"><p className="eyebrow">KHOLLELAB</p><h1 id="welcome-title">Les maths comme à l’oral.</h1><p>Un exercice, un tableau, un professeur qui s’adapte.</p><Link className="primary-cta" href={destination} aria-label="Commencer une khôlle">Commencer <ArrowRight aria-hidden="true"/></Link></section>:<><section className="dashboard-intro"><div><p className="eyebrow">Où en suis-je ?</p><h1>{data.account?.authenticated&&data.account.display_name?`Bonjour ${data.account.display_name}`:"Mon parcours"}</h1></div><Link className="primary-cta" href={destination} aria-label={cta}>{cta} <ArrowRight aria-hidden="true"/></Link></section>{loading?<CurriculumProgressSkeleton/>:data.progress?<CurriculumProgressCard progress={data.progress} metadata={data.curriculum}/>:<section className="curriculum-card unavailable"><h2>Progression momentanément indisponible</h2><p>Vous pouvez tout de même poursuivre votre khôlle.</p></section>}<div className="landing-grid"><RecentActivity sessions={data.sessions} error={data.errors.has("sessions")}/><PracticeSummary progression={data.progression} error={data.errors.has("progression")}/></div></>}{newLearner&&<section className="principles" aria-label="Comment fonctionne KHOLLELAB"><article><h2>Résous</h2><p>Écris ton raisonnement sur le tableau.</p></article><article><h2>Comprends</h2><p>Le professeur analyse ta démarche et t’aide.</p></article><article><h2>Progresse</h2><p>KholleLab choisit progressivement les exercices adaptés.</p></article></section>}</main>{accountOpen&&<AccountDialog account={data.account??{authenticated:false,anonymous_sessions_available:0}} onAccount={()=>{setAccountOpen(false);void load()}} onClose={()=>setAccountOpen(false)}/>} {data.account?.authenticated&&<button className="landing-logout" onClick={async()=>{await logoutAccount();await load()}}>Se déconnecter</button>}</div>
}
