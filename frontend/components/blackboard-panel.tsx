"use client";
import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from "react";
import {MathContent} from "./math-content";
import {HybridBlackboard,type HybridBlackboardHandle} from "./blackboard/HybridBlackboard";
import {useAttemptStore} from "@/stores/useAttemptStore";
const labels={idle:"Brouillon local",dirty:"Brouillon local",saving:"Sauvegarde…",saved:"Enregistré",error:"Hors ligne — copie conservée localement",conflict:"⚠ Conflit de version"};
export interface BlackboardPanelHandle{openKeyboard:()=>void;togglePreview:()=>void;requestSubmit:()=>void}
export const BlackboardPanel=forwardRef<BlackboardPanelHandle,{problemId?:string}>(function BlackboardPanel({problemId},forwardedRef){
 const s=useAttemptStore(),timer=useRef<ReturnType<typeof setTimeout>>(),board=useRef<HybridBlackboardHandle>(null);const[confirm,setConfirm]=useState(false),[preview,setPreview]=useState(false);
 useImperativeHandle(forwardedRef,()=>({openKeyboard:()=>board.current?.openKeyboard(),togglePreview:()=>setPreview(v=>!v),requestSubmit:()=>setConfirm(true)}),[]);
 useEffect(()=>{if(problemId)void useAttemptStore.getState().load(problemId);return()=>useAttemptStore.getState().reset()},[problemId]);
 useEffect(()=>{const interval=setInterval(()=>useAttemptStore.getState().tick(),1000);return()=>clearInterval(interval)},[]);
 useEffect(()=>{if(s.saveState==="dirty"){clearTimeout(timer.current);timer.current=setTimeout(()=>void useAttemptStore.getState().save(),1000)}return()=>clearTimeout(timer.current)},[s.solution,s.saveState]);
 const time=new Date(s.elapsedSeconds*1000).toISOString().slice(11,19);
 return <section className="panel board"><div className="board-head"><div className="eyebrow">Tableau</div><span className={`save ${s.saveState}`}>● {s.status==="submitted"?"Solution présentée":labels[s.saveState]}</span><span className="timer">{time}</span></div>{s.recovery&&<div className="notice">Une version locale plus récente de votre tableau a été trouvée.<button onClick={()=>s.updateSolution(s.recovery!)}>Restaurer</button><button onClick={s.useServer}>Utiliser la version serveur</button></div>}{s.status==="submitted"?<div className="submitted-copy" aria-label="Copie présentée"><MathContent content={s.solution}/></div>:<HybridBlackboard ref={board} solution={s.solution} onChange={s.updateSolution}/>}<button className="preview-toggle" type="button" onClick={()=>setPreview(!preview)}>{preview?"Masquer l’aperçu":"Aperçu de la copie"}</button>{preview&&<div className="copy-preview"><MathContent content={s.solution}/></div>}<button className="submit" disabled={!s.solution.trim()||s.saveState==="saving"||s.status==="submitted"} onClick={()=>setConfirm(true)}>Présenter ma solution</button>{confirm&&<div className="modal" role="dialog"><b>Présenter cette solution ?</b><p>Vous ne pourrez plus modifier cette tentative.</p><button onClick={()=>setConfirm(false)}>Annuler</button><button onClick={()=>{setConfirm(false);void s.submit()}}>Présenter</button></div>}</section>
});
