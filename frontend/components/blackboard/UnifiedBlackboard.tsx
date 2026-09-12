"use client";
import {forwardRef,useCallback,useEffect,useImperativeHandle,useRef,useState} from "react";
import type {MathfieldElement,VirtualKeyboardKeycap,VirtualKeyboardLayout} from "mathlive";
import {isSolutionEmpty,mathLiveToUnifiedSolution,unifiedSolutionToMathLive} from "@/lib/solution-document";

const lineBreakKeycap:Partial<VirtualKeyboardKeycap>={label:"↵",command:"addRowAfter",class:"action",width:1.5};
const layouts:VirtualKeyboardLayout[]=[
 {id:"kholle-basic",label:"Basique",rows:[["7","8","9","+","-","[backspace]"],["4","5","6","\\times","\\div","="],["1","2","3","(",")","\\frac{#@}{#?}"],["0",".","x^2","x^{#?}","\\sqrt{#0}","[left]","[right]"],["["," ]","<",">","\\le","\\ge","\\ne",lineBreakKeycap]]},
 {id:"kholle-functions",label:"Fonctions",rows:[["\\sin","\\cos","\\tan"],["\\ln","\\exp","\\log"]]},
 {id:"kholle-analysis",label:"Analyse",rows:[["\\lim_{#?}","\\sum_{#?}^{#?}","\\int_{#?}^{#?}"],["\\infty","\\pm","\\to"]]},
 {id:"kholle-sets",label:"Ensembles",rows:[["\\mathbb{N}","\\mathbb{Z}","\\mathbb{Q}","\\mathbb{R}","\\mathbb{C}"],["\\in","\\notin","\\subset","\\subseteq","\\cup","\\cap"],["\\forall","\\exists"]]},
 {id:"kholle-greek",label:"Grec",rows:[["\\alpha","\\beta","\\gamma","\\delta","\\theta","\\lambda","\\mu"],["\\pi","\\sigma","\\phi","\\omega","\\Delta","\\Sigma","\\Omega"]]},
];

export interface UnifiedBlackboardHandle{toggleKeyboard:()=>void;insertLineBreak:()=>void}
export const UnifiedBlackboard=forwardRef<UnifiedBlackboardHandle,{solution:string;onChange:(value:string)=>void;readOnly?:boolean}>(function UnifiedBlackboard({solution,onChange,readOnly=false},ref){
 const host=useRef<HTMLDivElement>(null),field=useRef<MathfieldElement|null>(null),change=useRef(onChange),last=useRef(solution),locked=useRef(readOnly),composing=useRef(false),compositionChanged=useRef(false);change.current=onChange;locked.current=readOnly;
 const[failed,setFailed]=useState(false),[keyboardOpen,setKeyboardOpen]=useState(false);
 const insertLineBreak=useCallback(()=>{const mf=field.current;if(!mf||locked.current)return;mf.focus();mf.executeCommand("addRowAfter");mf.focus()},[]);
 const setNativeInput=useCallback((mf:MathfieldElement,enabled:boolean)=>{const sink=mf.shadowRoot?.querySelector<HTMLElement>("[part=keyboard-sink]");if(!sink)return;sink.setAttribute("inputmode",enabled?"text":"none");sink.setAttribute("enterkeyhint","enter");sink.setAttribute("autocapitalize","sentences");sink.setAttribute("autocorrect","on");sink.spellcheck=enabled},[]);
 useImperativeHandle(ref,()=>({toggleKeyboard(){const mf=field.current;if(!mf||locked.current)return;if(window.mathVirtualKeyboard.visible){window.mathVirtualKeyboard.hide();setNativeInput(mf,true);return}setNativeInput(mf,false);mf.focus();window.mathVirtualKeyboard.show();},insertLineBreak}),[insertLineBreak,setNativeInput]);
 useEffect(()=>{let disposed=false;const node=host.current;void import("mathlive").then(()=>{if(disposed||!node)return;const mf=document.createElement("math-field") as MathfieldElement;
   mf.defaultMode="text";mf.smartMode=true;mf.smartFence=true;mf.letterShapeStyle="french";mf.mathVirtualKeyboardPolicy="manual";mf.placeholder="\\text{Expliquez votre raisonnement…}";mf.readOnly=readOnly;mf.setAttribute("aria-label","Tableau de résolution");mf.className="unified-blackboard";
   window.mathVirtualKeyboard.alphabeticLayout="azerty";window.mathVirtualKeyboard.layouts=[...layouts,"alphabetic"];window.mathVirtualKeyboard.setKeycap("[return]",lineBreakKeycap);
   mf.setValue(unifiedSolutionToMathLive(solution),{selectionMode:"after"});mf.position=Math.max(0,mf.lastOffset-1);last.current=solution;
   const publish=()=>{const exported=mathLiveToUnifiedSolution(mf.value);const value=isSolutionEmpty(exported)?"":exported;if(value===last.current)return;last.current=value;change.current(value)};
   mf.addEventListener("compositionstart",()=>{composing.current=true;compositionChanged.current=false});
   mf.addEventListener("compositionend",()=>{composing.current=false;if(compositionChanged.current)publish();compositionChanged.current=false});
   mf.addEventListener("input",()=>{if(composing.current){compositionChanged.current=true;return}publish()});node.replaceChildren(mf);field.current=mf;setNativeInput(mf,!readOnly);
   // MathLive 0.110 does not consistently focus its keyboard sink after a
   // touch tap on empty content. Focus once after pointer placement; subsequent
   // taps are left entirely to MathLive so they can reposition the caret.
   const focusFromTouch=()=>{if(!locked.current&&!mf.hasFocus())mf.focus()};mf.addEventListener("pointerup",focusFromTouch);
   const enter=(event:KeyboardEvent)=>{if(event.key!=="Enter"||event.ctrlKey||event.metaKey||event.altKey||event.defaultPrevented||locked.current)return;event.preventDefault();insertLineBreak()};mf.addEventListener("keydown",enter);
   const shadow=mf.shadowRoot;const imeEnter=(event:Event)=>{const input=event as InputEvent;if((input.inputType!=="insertParagraph"&&input.inputType!=="insertLineBreak")||locked.current)return;event.preventDefault();insertLineBreak()};shadow?.addEventListener("beforeinput",imeEnter,{capture:true});
   const toggle=()=>{const visible=window.mathVirtualKeyboard.visible;setKeyboardOpen(visible);setNativeInput(mf,!visible&&!locked.current)};window.mathVirtualKeyboard.addEventListener("virtual-keyboard-toggle",toggle);(mf as MathfieldElement&{__cleanup?:()=>void}).__cleanup=()=>{window.mathVirtualKeyboard.removeEventListener("virtual-keyboard-toggle",toggle);shadow?.removeEventListener("beforeinput",imeEnter,{capture:true});mf.removeEventListener("pointerup",focusFromTouch)};
 }).catch(()=>!disposed&&setFailed(true));return()=>{disposed=true;(field.current as (MathfieldElement&{__cleanup?:()=>void})|null)?.__cleanup?.();field.current=null;node?.replaceChildren()};// created once: external synchronization is handled separately
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[]);
 useEffect(()=>{const mf=field.current;if(mf&&solution!==last.current){const next=unifiedSolutionToMathLive(solution);if(mf.value!==next){mf.setValue(next,{selectionMode:"after"});mf.position=Math.max(0,mf.lastOffset-1)}last.current=solution}},[solution]);
 useEffect(()=>{const mf=field.current;if(mf){mf.readOnly=readOnly;setNativeInput(mf,!readOnly&&!window.mathVirtualKeyboard?.visible)}if(readOnly&&window.mathVirtualKeyboard?.visible)window.mathVirtualKeyboard.hide()},[readOnly,setNativeInput]);
 if(failed)return <div className="unified-blackboard-error" role="alert">L’éditeur mathématique n’a pas pu être chargé.</div>;
 return <div ref={host} className={`unified-blackboard-shell${keyboardOpen?" keyboard-open":""}`} />;
});
