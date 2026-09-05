"use client";
import {useState} from "react";

const essential = [
  ..."0123456789".split("").map(x=>[x,x]), ["+","+"],["−","-"],["×","\\times"],["÷","\\div"],["=","="],
  ["(","("],[")",")"],["[","["],["]","]"],["x²","#@^{2}"],["xⁿ","#@^{#?}"],["√","\\sqrt{#0}"],["fraction","\\frac{#@}{#?}"],["|x|","\\left|#@\\right|"],
  ["<","<"],[">",">"],["≤","\\le"],["≥","\\ge"],["≠","\\ne"],["←","moveToPreviousChar"],["→","moveToNextChar"],["⌫","deleteBackward"]
] as const;
const layouts = {
  Essentiel: essential,
  Fonctions: [["sin","\\sin"],["cos","\\cos"],["tan","\\tan"],["ln","\\ln"],["exp","\\exp"],["f(x)","f(#0)"],["(x)","\\left(#@\\right)"]],
  Analyse: [["lim","\\lim_{#0\\to#?}"],["∑","\\sum_{#0}^{#?}"],["∫","\\int_{#0}^{#?}"],["∞","\\infty"],["±","\\pm"],["→","\\to"]],
  Ensembles: [["ℕ","\\mathbb{N}"],["ℤ","\\mathbb{Z}"],["ℚ","\\mathbb{Q}"],["ℝ","\\mathbb{R}"],["ℂ","\\mathbb{C}"],["∈","\\in"],["∪","\\cup"],["∩","\\cap"],["∀","\\forall"],["∃","\\exists"]],
  Grec: ["alpha","beta","gamma","delta","theta","lambda","pi","sigma","phi","omega","Delta","Sigma","Omega"].map(name=>[name==="Delta"?"Δ":name,`\\${name}`])
} as const;

export function ScientificMathDock({open,onClose,onInsert}:{open:boolean;onClose:()=>void;onInsert:(value:string)=>void}){
  const [tab,setTab]=useState<keyof typeof layouts>("Essentiel");
  if(!open)return null;
  return <section className="scientific-math-dock" aria-label="Clavier scientifique"><div className="dock-head"><b>Clavier scientifique</b><button onClick={onClose} aria-label="Fermer le clavier">×</button></div><div className="keyboard-tabs" role="tablist">{Object.keys(layouts).map(name=><button key={name} role="tab" aria-selected={tab===name} className={tab===name?"active":""} onPointerDown={e=>e.preventDefault()} onClick={()=>setTab(name as keyof typeof layouts)}>{name}</button>)}</div><div className="keyboard-keys">{layouts[tab].map(([label,value])=><button type="button" key={label} aria-label={`Insérer ${label}`} onPointerDown={e=>{e.preventDefault();onInsert(value)}}>{label}</button>)}</div></section>
}
