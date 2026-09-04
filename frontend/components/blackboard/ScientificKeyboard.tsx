"use client";
import { useEffect, useState } from "react";
const layouts = {
  Essentiel: [["=","="],["≠","\\ne"],["≤","\\le"],["≥","\\ge"],["√","\\sqrt{#0}"],["a/b","\\frac{#0}{#?}"],["x²","^{2}"]],
  Fonctions: [["sin","\\sin"],["cos","\\cos"],["tan","\\tan"],["ln","\\ln"],["log","\\log"],["exp","\\exp"],["f(x)","f(#0)"],["f′(x)","f'(#0)"],["x↦f(x)","x\\mapsto f(x)"]],
  Analyse: [["lim","\\lim_{#0\\to#?}"],["∑","\\sum_{#0}^{#?}"],["∏","\\prod_{#0}^{#?}"],["∫","\\int_{#0}^{#?}"],["∞","\\infty"],["dx","\\,dx"],["→","\\to"],["vecteur","\\vec{#0}"],["matrice 2×2","\\begin{pmatrix}#0&#?\\\\#?&#?\\end{pmatrix}"]],
  Ensembles: [["ℕ","\\mathbb{N}"],["ℤ","\\mathbb{Z}"],["ℚ","\\mathbb{Q}"],["ℝ","\\mathbb{R}"],["ℂ","\\mathbb{C}"],["∈","\\in"],["∉","\\notin"],["⊂","\\subset"],["⊆","\\subseteq"],["∪","\\cup"],["∩","\\cap"],["∀","\\forall"],["∃","\\exists"],["⇒","\\Rightarrow"],["⇔","\\Leftrightarrow"],["¬","\\neg"],["∅","\\varnothing"]],
  Grec: ["alpha","beta","gamma","delta","epsilon","theta","lambda","mu","pi","rho","sigma","phi","psi","omega","Delta","Sigma","Omega"].map((name) => [`\\${name}`,`\\${name}`]),
} satisfies Record<string, readonly (readonly [string,string])[]>;
export function ScientificKeyboard({ onInsert, curriculumLevel }: { onInsert: (latex: string) => void; curriculumLevel?: string }) {
  const [open,setOpen]=useState(false); const [tab,setTab]=useState<keyof typeof layouts>("Essentiel");
  const toggle=()=>{const next=!open;setOpen(next);if(window.mathVirtualKeyboard){if(next)window.mathVirtualKeyboard.show();else window.mathVirtualKeyboard.hide()}};
  useEffect(() => { const close=(event:KeyboardEvent)=>{if(event.key==="Escape"){setOpen(false);window.mathVirtualKeyboard?.hide()}}; addEventListener("keydown",close); return()=>removeEventListener("keydown",close)},[]);
  return <div className="scientific-keyboard" data-curriculum-level={curriculumLevel}><button type="button" className="keyboard-toggle" aria-expanded={open} onClick={toggle}>⌨ Clavier scientifique</button>{open&&<div className="keyboard-dock"><div className="keyboard-tabs">{Object.keys(layouts).map(name=><button type="button" className={tab===name?"active":""} key={name} onClick={()=>setTab(name as keyof typeof layouts)}>{name}</button>)}</div><div className="keyboard-keys">{layouts[tab].map(([label,latex])=><button type="button" aria-label={`Insérer ${label}`} key={label} onPointerDown={e=>e.preventDefault()} onMouseDown={e=>e.preventDefault()} onClick={()=>onInsert(latex)}>{label}</button>)}</div></div>}</div>;
}
