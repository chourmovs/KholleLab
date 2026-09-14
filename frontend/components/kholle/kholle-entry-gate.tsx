"use client";
import {useCallback,useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {getActiveSession,getCurriculumProgress} from "@/lib/api";
import {KholleWorkspace} from "./kholle-workspace";

type GateState="loading"|"authorized"|"redirecting"|"error";
export function KholleEntryGate(){
 const router=useRouter(),[state,setState]=useState<GateState>("loading");
 const check=useCallback(async()=>{setState("loading");try{const progress=await getCurriculumProgress();if(progress.onboarding_completed){setState("authorized");return}const active=await getActiveSession();if(active){setState("authorized");return}setState("redirecting");router.replace("/onboarding")}catch{setState("error")}},[router]);
 useEffect(()=>{queueMicrotask(()=>void check())},[check]);
 if(state==="authorized")return <KholleWorkspace/>;
 if(state==="error")return <main className="entry-state"><h1>Impossible d’ouvrir la khôlle</h1><p>Nous n’avons pas pu vérifier ton parcours.</p><button onClick={()=>void check()}>Réessayer</button></main>;
 // Keep the route's semantic <main> reserved for the workspace. In particular,
 // this prevents assistive technology (and browser automation) from latching on
 // to a transient main landmark which disappears as authorization resolves.
 return <div className="entry-state" role="status" aria-live="polite"><p>{state==="redirecting"?"Redirection vers le choix du niveau…":"Vérification de ton parcours…"}</p></div>;
}
