"use client";
import {useCallback,useEffect,useRef,useState} from "react";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {WorkspaceLayout,BlackboardToolRail} from "@/components/workspace-layout";
import {AppHeader} from "@/components/app-header";
import {BlackboardPanel,type BlackboardPanelHandle} from "@/components/blackboard-panel";
import {ProblemPanel} from "@/components/problem-panel";
import {ProfessorPanel} from "@/components/professor-panel";
import {ApiError,abandonSession,getCurriculum,getHealth,getInferenceStatus,getNextProblem,getProblem} from "@/lib/api";
import type {CurriculumMetadata,ProblemDetail,SelectionAdaptation} from "@/lib/types";
import type {HealthStatus,InferenceStatus} from "@/lib/api";
import {SessionHistory} from "@/components/session-history";
import {LearnerProfileView} from "@/components/learner-profile";
import {useAttemptStore} from "@/stores/useAttemptStore";

type WorkspaceState="loading"|"ready"|"unavailable"|"invalid-level"|"error";
export function KholleWorkspace({legacyActiveProblemId}:{legacyActiveProblemId?:string}){
  const router=useRouter(),attemptStatus=useAttemptStore(s=>s.status),sessionId=useAttemptStore(s=>s.sessionId);
  const[history,setHistory]=useState(false),[profile,setProfile]=useState(false),[statementExpanded,setStatementExpanded]=useState(true);
  const[inference,setInference]=useState<InferenceStatus>(),[health,setHealth]=useState<HealthStatus|null>();
  const[metadata,setMetadata]=useState<CurriculumMetadata>(),[problem,setProblem]=useState<ProblemDetail|null>();
  const[adaptation,setAdaptation]=useState<SelectionAdaptation>(),[state,setState]=useState<WorkspaceState>("loading");
  const boardRef=useRef<BlackboardPanelHandle>(null),problemIdRef=useRef<string|undefined>(undefined),initialized=useRef(false);
  const acceptProblem=useCallback((next:ProblemDetail)=>{if(next.id!==problemIdRef.current){problemIdRef.current=next.id;setStatementExpanded(true)}setProblem(next)},[]);
  const loadGuidedProblem=useCallback(async()=>{setState("loading");setAdaptation(undefined);try{const result=await getNextProblem();useAttemptStore.getState().reset();acceptProblem(result.problem);setAdaptation(result.adaptation);setState("ready")}catch(error){if(error instanceof ApiError){const code=error.payload?.detail??error.payload?.error;if(code==="onboarding_required"){router.replace("/onboarding");return}if(code==="guided_problem_unavailable"){setState("unavailable");return}if(code==="current_level_invalid"){setState("invalid-level");return}}setState("error")}},[acceptProblem,router]);
  const refreshInference=useCallback(async(force=false)=>{try{setInference(await getInferenceStatus(force))}catch{setInference({provider:"huggingface",status:"unavailable",family:"qwen",fast_model:"Qwen3-8B",fast_backend:"nscale",deep_model:"Qwen3-32B",deep_backend:"nscale",reason:"connection_failed"})}},[]);
  useEffect(()=>{let timer:ReturnType<typeof setTimeout>,cancelled=false;const poll=async()=>{await refreshInference();try{setHealth(await getHealth())}catch{setHealth(null)}if(!cancelled)timer=setTimeout(()=>void poll(),60_000)};void poll();return()=>{cancelled=true;clearTimeout(timer)}},[refreshInference]);
  useEffect(()=>{if(initialized.current)return;initialized.current=true;let cancelled=false;queueMicrotask(async()=>{getCurriculum().then(value=>{if(!cancelled)setMetadata(value)}).catch(()=>{});if(legacyActiveProblemId){setState("loading");try{const restored=await getProblem(legacyActiveProblemId);if(!cancelled){useAttemptStore.getState().reset();acceptProblem(restored);setState("ready")}}catch{if(!cancelled)setState("error")}}else if(!cancelled)await loadGuidedProblem()});return()=>{cancelled=true}},[acceptProblem,legacyActiveProblemId,loadGuidedProblem]);
  async function skipProblem(){if(attemptStatus!=="draft"||!sessionId)return;if(!window.confirm("Cet exercice sera marqué comme abandonné. Votre travail actuel restera enregistré dans l’historique. Continuer ?"))return;try{await abandonSession(sessionId);await loadGuidedProblem()}catch{setState("error")}}
  if(profile)return <main><LearnerProfileView onClose={()=>setProfile(false)}/></main>;
  if(history)return <main><SessionHistory onClose={()=>setHistory(false)} onResume={async session=>{useAttemptStore.getState().reset();acceptProblem(await getProblem(session.problem_id));await useAttemptStore.getState().load(session.problem_id);setState("ready");setHistory(false)}}/></main>;
  const errorPanel=state==="unavailable"?<section className="panel problem state"><p>Aucun exercice guidé n’est disponible pour ce niveau.</p><button onClick={()=>void loadGuidedProblem()}>Réessayer</button><Link href="/">Retour à l’accueil</Link></section>:state==="invalid-level"?<section className="panel problem state"><p>Le niveau actuel de votre parcours est invalide. Revenez à l’accueil pour le corriger.</p><button onClick={()=>void loadGuidedProblem()}>Réessayer</button><Link href="/">Retour à l’accueil</Link></section>:state==="error"?<section className="panel problem state"><p>Impossible de charger l’exercice guidé.</p><button onClick={()=>void loadGuidedProblem()}>Réessayer</button><Link href="/">Retour à l’accueil</Link></section>:null;
  return <main><div className="shell"><AppHeader health={health} inference={inference} onRefresh={()=>void refreshInference(true)} onHistory={()=>setHistory(true)} onProfile={()=>setProfile(true)}/>{state==="ready"&&attemptStatus==="draft"&&<nav className="guided-navigation" aria-label="Actions de l’exercice"><button onClick={()=>void skipProblem()}>Passer cet exercice</button></nav>}<WorkspaceLayout statementExpanded={statementExpanded} tools={<BlackboardToolRail submitted={attemptStatus==="submitted"} problemId={problem?.id} onKeyboard={()=>boardRef.current?.openKeyboard()} onDictation={text=>boardRef.current?.insertText(text)} onSubmit={()=>boardRef.current?.requestSubmit()}/>} statement={state==="loading"?<section className="panel problem state">Chargement de la khôlle…</section>:errorPanel??(problem&&<ProblemPanel problem={problem} levelLabel={metadata?.levels.find(item=>item.id===problem.curriculum.level)?.label} adaptation={adaptation} expanded={statementExpanded} onExpandedChange={setStatementExpanded}/>)} blackboard={<BlackboardPanel ref={boardRef} problemId={problem?.id}/>} professor={<ProfessorPanel onNextExercise={loadGuidedProblem}/>}/></div><footer>Prototype 0.5.0</footer></main>;
}
