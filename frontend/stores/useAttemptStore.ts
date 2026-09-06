import {create} from "zustand";
import {ApiError,createAttempt,getAttempt,patchAttempt,submitAttempt} from "@/lib/api";
import type {Attempt,AttemptStatus} from "@/lib/types";

export type SaveState="idle"|"dirty"|"saving"|"saved"|"error"|"conflict";
type State={attemptId?:string;problemId?:string;status:AttemptStatus;solution:string;revision:number;elapsedSeconds:number;saveState:SaveState;serverAttempt?:Attempt;recovery?:string;editGeneration:number;loadGeneration:number;load:(p:string)=>Promise<void>;updateSolution:(s:string)=>void;tick:()=>void;save:()=>Promise<boolean>;submit:()=>Promise<void>;useServer:()=>void;keepLocal:()=>Promise<void>;reset:()=>void};
const draftKey=(id:string)=>`khollelab.draft.${id}`,currentKey=(p:string)=>`khollelab.currentAttempt.${p}`;
let savePromise:Promise<boolean>|undefined;
let saveRunnerGeneration=0;
let loadGeneration=0;
function draft(id:string){try{return JSON.parse(localStorage.getItem(draftKey(id))??"null") as {solution:string;updatedAt:string;serverRevision:number}|null}catch{return null}}
function values(a:Attempt){const d=draft(a.id);return{attemptId:a.id,problemId:a.problem_id,status:a.status,solution:a.solution_markdown,revision:a.revision,elapsedSeconds:a.elapsed_seconds,saveState:"saved" as SaveState,serverAttempt:a,recovery:d&&d.solution!==a.solution_markdown&&Date.parse(d.updatedAt)>Date.parse(a.updated_at)?d.solution:undefined}}

export const useAttemptStore=create<State>((set,get)=>({
  status:"draft",solution:"",revision:0,elapsedSeconds:0,saveState:"idle",editGeneration:0,loadGeneration:0,
  async load(problemId){
    const generation=++loadGeneration;
    set({loadGeneration:generation});
    const id=localStorage.getItem(currentKey(problemId));let attempt:Attempt|undefined;
    if(id)try{attempt=await getAttempt(id)}catch(error){if(error instanceof ApiError&&error.status===404)localStorage.removeItem(currentKey(problemId));else throw error}
    if(generation!==loadGeneration)return;
    if(!attempt){attempt=await createAttempt(problemId);if(generation!==loadGeneration)return;if(!attempt){set({saveState:"error"});return}localStorage.setItem(currentKey(problemId),attempt.id)}
    set({...values(attempt),editGeneration:0,loadGeneration:generation});
  },
  updateSolution(solution){const state=get();if(!state.attemptId||state.status==="submitted")return;const editGeneration=state.editGeneration+1;localStorage.setItem(draftKey(state.attemptId),JSON.stringify({solution,updatedAt:new Date().toISOString(),serverRevision:state.revision}));set({solution,editGeneration,saveState:"dirty"})},
  tick(){if(get().status==="draft")set(state=>({elapsedSeconds:state.elapsedSeconds+1}))},
  async save(){
    if(savePromise)return savePromise;
    const runnerGeneration=++saveRunnerGeneration;
    savePromise=(async()=>{
      for(;;){
        const snapshot=get();
        if(!snapshot.attemptId||snapshot.status!=="draft")return snapshot.saveState==="saved";
        if(snapshot.saveState==="saved")return true;
        set({saveState:"saving"});
        try{
          const saved=await patchAttempt(snapshot.attemptId,snapshot.solution,snapshot.elapsedSeconds,snapshot.revision);
          const current=get();
          if(current.attemptId!==snapshot.attemptId)return false;
          localStorage.setItem(draftKey(saved.id),JSON.stringify({solution:current.editGeneration===snapshot.editGeneration?saved.solution_markdown:current.solution,updatedAt:new Date().toISOString(),serverRevision:saved.revision}));
          if(current.editGeneration===snapshot.editGeneration){set({...values(saved),editGeneration:current.editGeneration,recovery:undefined});return true}
          // A response may advance the server revision, but never replace newer local text.
          set({revision:saved.revision,serverAttempt:saved,saveState:"dirty",recovery:undefined});
        }catch(error){
          const current=get();
          if(current.attemptId!==snapshot.attemptId)return false;
          set({saveState:error instanceof ApiError&&error.status===409?"conflict":"error"});return false;
        }
      }
    })().finally(()=>{if(runnerGeneration===saveRunnerGeneration)savePromise=undefined});
    return savePromise;
  },
  async submit(){
    while(get().saveState!=="saved"&&await get().save()){/* flush edits made during an earlier PATCH */}
    const snapshot=get();if(!snapshot.attemptId||snapshot.saveState!=="saved")return;
    const submitted=await submitAttempt(snapshot.attemptId,snapshot.revision);
    if(get().attemptId===snapshot.attemptId)set({...values(submitted),editGeneration:get().editGeneration});
  },
  useServer(){const attempt=get().serverAttempt;if(attempt)set({...values(attempt),editGeneration:get().editGeneration+1,recovery:undefined})},
  async keepLocal(){const state=get();if(!state.attemptId)return;const latest=await getAttempt(state.attemptId);if(get().attemptId!==state.attemptId)return;set({revision:latest.revision,status:latest.status,serverAttempt:latest,recovery:undefined,saveState:"dirty"});await get().save()},
  reset(){loadGeneration++;saveRunnerGeneration++;savePromise=undefined;set({attemptId:undefined,problemId:undefined,status:"draft",solution:"",revision:0,elapsedSeconds:0,saveState:"idle",serverAttempt:undefined,recovery:undefined,editGeneration:0,loadGeneration})}
}));
