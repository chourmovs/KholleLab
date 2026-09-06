"use client";
import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from "react";
import type {MathfieldElement,VirtualKeyboardLayout} from "mathlive";
import {legacySolutionToMathLive,isSolutionEmpty} from "@/lib/solution-document";

const layouts:VirtualKeyboardLayout[]=[
 {id:"kholle-basic",label:"Basique",rows:[["7","8","9","+","-","[backspace]"],["4","5","6","\\times","\\div","="],["1","2","3","(",")","\\frac{#@}{#?}"],["0",".","x^2","x^{#?}","\\sqrt{#0}","[left]","[right]"],["["," ]","<",">","\\le","\\ge","\\ne"]]},
 {id:"kholle-functions",label:"Fonctions",rows:[["\\sin","\\cos","\\tan"],["\\ln","\\exp","\\log"]]},
 {id:"kholle-analysis",label:"Analyse",rows:[["\\lim_{#?}","\\sum_{#?}^{#?}","\\int_{#?}^{#?}"],["\\infty","\\pm","\\to"]]},
 {id:"kholle-sets",label:"Ensembles",rows:[["\\mathbb{N}","\\mathbb{Z}","\\mathbb{Q}","\\mathbb{R}","\\mathbb{C}"],["\\in","\\notin","\\subset","\\subseteq","\\cup","\\cap"],["\\forall","\\exists"]]},
 {id:"kholle-greek",label:"Grec",rows:[["\\alpha","\\beta","\\gamma","\\delta","\\theta","\\lambda","\\mu"],["\\pi","\\sigma","\\phi","\\omega","\\Delta","\\Sigma","\\Omega"]]},
];

export interface UnifiedBlackboardHandle{toggleKeyboard:()=>void}
export const UnifiedBlackboard=forwardRef<UnifiedBlackboardHandle,{solution:string;onChange:(value:string)=>void;readOnly?:boolean}>(function UnifiedBlackboard({solution,onChange,readOnly=false},ref){
 const host=useRef<HTMLDivElement>(null),field=useRef<MathfieldElement|null>(null),change=useRef(onChange),last=useRef(solution);change.current=onChange;
 const[failed,setFailed]=useState(false),[keyboardOpen,setKeyboardOpen]=useState(false);
 useImperativeHandle(ref,()=>({toggleKeyboard(){const mf=field.current;if(!mf||readOnly)return;mf.focus();if(window.mathVirtualKeyboard.visible)window.mathVirtualKeyboard.hide();else window.mathVirtualKeyboard.show();}}),[readOnly]);
 useEffect(()=>{let disposed=false;const node=host.current;void import("mathlive").then(()=>{if(disposed||!node)return;const mf=document.createElement("math-field") as MathfieldElement;
   mf.defaultMode="text";mf.smartMode=true;mf.smartFence=true;mf.letterShapeStyle="french";mf.mathVirtualKeyboardPolicy="manual";mf.placeholder="\\text{Expliquez votre raisonnement…}";mf.readOnly=readOnly;mf.setAttribute("aria-label","Tableau de résolution");mf.className="unified-blackboard";
   window.mathVirtualKeyboard.alphabeticLayout="azerty";window.mathVirtualKeyboard.layouts=[...layouts,"alphabetic"];
   mf.value=legacySolutionToMathLive(solution);last.current=solution;mf.addEventListener("input",()=>{const value=isSolutionEmpty(mf.value)?"":mf.value;last.current=value;change.current(value)});node.replaceChildren(mf);field.current=mf;
   const toggle=()=>setKeyboardOpen(window.mathVirtualKeyboard.visible);window.mathVirtualKeyboard.addEventListener("virtual-keyboard-toggle",toggle);(mf as MathfieldElement&{__cleanup?:()=>void}).__cleanup=()=>window.mathVirtualKeyboard.removeEventListener("virtual-keyboard-toggle",toggle);
 }).catch(()=>!disposed&&setFailed(true));return()=>{disposed=true;(field.current as (MathfieldElement&{__cleanup?:()=>void})|null)?.__cleanup?.();field.current=null;node?.replaceChildren()};// created once: external synchronization is handled separately
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[]);
 useEffect(()=>{const mf=field.current;if(mf&&solution!==last.current){const next=legacySolutionToMathLive(solution);if(mf.value!==next)mf.value=next;last.current=solution}},[solution]);
 useEffect(()=>{if(field.current)field.current.readOnly=readOnly;if(readOnly&&window.mathVirtualKeyboard?.visible)window.mathVirtualKeyboard.hide()},[readOnly]);
 if(failed)return <div className="unified-blackboard-error" role="alert">L’éditeur mathématique n’a pas pu être chargé.</div>;
 return <div ref={host} className={`unified-blackboard-shell${keyboardOpen?" keyboard-open":""}`} onClick={()=>field.current?.focus()} />;
});
