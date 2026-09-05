"use client";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { parseSolutionMarkdown, serializeSolutionDocument, solutionBlockId, type SolutionBlock, type SolutionDocument } from "@/lib/solution-document";
import { MathEquationEditor, type MathEquationEditorHandle } from "./MathEquationEditor";
import { ScientificMathDock } from "./ScientificMathDock";
import { TextBlockEditor } from "./TextBlockEditor";
import { MathFieldRegistry } from "./MathFieldRegistry";

export interface HybridBlackboardHandle { openKeyboard:()=>void }
export const HybridBlackboard=forwardRef<HybridBlackboardHandle,{ solution: string; onChange: (markdown: string) => void; curriculumLevel?: string }>(function HybridBlackboard({ solution, onChange },forwardedRef) {
  const [document,setDocument]=useState<SolutionDocument>(()=>parseSolutionMarkdown(solution));
  const [activeMathBlockId,setActiveMathBlockId]=useState<string>();
  const [dockOpen,setDockOpen]=useState(false);
  const refs=useRef(new Map<string,MathEquationEditorHandle>()); const registry=useRef(new MathFieldRegistry()); const lastSerializedValueRef=useRef(solution);
  useEffect(()=>{if(solution!==lastSerializedValueRef.current){setDocument(parseSolutionMarkdown(solution));lastSerializedValueRef.current=solution}},[solution]);
  const commit=useCallback((next:SolutionDocument)=>{setDocument(next);const markdown=serializeSolutionDocument(next);lastSerializedValueRef.current=markdown;onChange(markdown)},[onChange]);
  const update=(id:string,value:string)=>commit({...document,blocks:document.blocks.map(block=>block.id===id?(block.type==="math"?{...block,latex:value}:{...block,content:value}):block)});
  const add=(after:number,type:SolutionBlock["type"])=>{const block:SolutionBlock=type==="math"?{id:solutionBlockId(),type,latex:""}:{id:solutionBlockId(),type,content:""};commit({...document,blocks:[...document.blocks.slice(0,after+1),block,...document.blocks.slice(after+1)]});if(type==="math")setTimeout(()=>refs.current.get(block.id)?.focus())};
  const remove=(index:number)=>{if(document.blocks.length===1)return;const next={...document,blocks:document.blocks.filter((_,i)=>i!==index)};commit(next);const previous=next.blocks[Math.max(0,index-1)];if(previous?.type==="math")setTimeout(()=>refs.current.get(previous.id)?.focus())};
  const insert=useCallback((latex:string)=>registry.current.insertMathTemplate(latex),[]);
  // `add` intentionally follows the current document snapshot.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const openKeyboard=useCallback(()=>{setDockOpen(true);const maths=document.blocks.filter(b=>b.type==="math");if(activeMathBlockId){setTimeout(()=>refs.current.get(activeMathBlockId)?.focus());return}if(maths.length){const id=maths.at(-1)!.id;setActiveMathBlockId(id);setTimeout(()=>refs.current.get(id)?.focus());return}add(document.blocks.length-1,"math")},[activeMathBlockId,document]);
  useImperativeHandle(forwardedRef,()=>({openKeyboard}),[openKeyboard]);
  return <div className="hybrid-blackboard">{document.blocks.map((block,index)=><div className={`solution-block ${block.type}`} key={block.id}>
    {block.type==="text"?<TextBlockEditor label={`Texte ${index+1}`} value={block.content} onChange={value=>update(block.id,value)} onAddMath={()=>add(index,"math")}/>:<MathEquationEditor ref={handle=>{if(handle){refs.current.set(block.id,handle);registry.current.register(block.id,handle)}else{refs.current.delete(block.id);registry.current.unregister(block.id)}}} value={block.latex} onChange={value=>update(block.id,value)} onFocus={()=>{registry.current.activate(block.id);setActiveMathBlockId(block.id)}} onEnter={()=>add(index,"text")} onDeleteEmpty={()=>remove(index)} label={`Équation ${index+1}`}/>}
    <div className="block-actions"><button type="button" aria-label={`Supprimer le bloc ${index+1}`} disabled={document.blocks.length===1} onClick={()=>remove(index)}>×</button><button type="button" onClick={()=>add(index,"text")}>+ Texte</button><button type="button" onClick={()=>add(index,"math")}>+ Équation</button></div>
  </div>)}<ScientificMathDock open={dockOpen} onClose={()=>setDockOpen(false)} onInsert={insert}/></div>;
});
