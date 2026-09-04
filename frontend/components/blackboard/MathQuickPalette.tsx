"use client";
export const QUICK_KEYS = [
 ["=","=","Égal"],["+","+","Plus"],["−","-","Moins"],["×","\\times","Multiplier"],["÷","\\div","Diviser"],["( )","\\left(#0\\right)","Parenthèses"],["[ ]","\\left[#0\\right]","Crochets"],
 ["x²","^{2}","Carré"],["xⁿ","^{#0}","Puissance"],["√","\\sqrt{#0}","Racine carrée"],["a/b","\\frac{#0}{#?}","Fraction"],["|x|","\\left|#0\\right|","Valeur absolue"],
 ["<","<","Inférieur"],[">",">","Supérieur"],["≤","\\le","Inférieur ou égal"],["≥","\\ge","Supérieur ou égal"],["≠","\\ne","Différent"],["⇒","\\Rightarrow","Implique"],["⇔","\\Leftrightarrow","Équivaut"],
 ["π","\\pi","Pi"],["∞","\\infty","Infini"],["sin","\\sin","Sinus"],["cos","\\cos","Cosinus"],["tan","\\tan","Tangente"],["ln","\\ln","Logarithme"],["exp","\\exp","Exponentielle"],["∑","\\sum_{#0}^{#?}","Somme"],["∫","\\int_{#0}^{#?}","Intégrale"],
 ["ℕ","\\mathbb{N}","Entiers naturels"],["ℤ","\\mathbb{Z}","Entiers relatifs"],["ℚ","\\mathbb{Q}","Rationnels"],["ℝ","\\mathbb{R}","Réels"],["ℂ","\\mathbb{C}","Complexes"],["∈","\\in","Appartient"],["∉","\\notin","N’appartient pas"],
 ["α","\\alpha","Alpha"],["β","\\beta","Bêta"],["θ","\\theta","Thêta"],["λ","\\lambda","Lambda"],["Δ","\\Delta","Delta"],
] as const;
export function MathQuickPalette({onInsert}:{onInsert:(latex:string)=>void}){return <div className="quick-palette" aria-label="Symboles mathématiques rapides">{QUICK_KEYS.map(([text,latex,label])=><button key={label} type="button" title={label} aria-label={label} onPointerDown={event=>event.preventDefault()} onMouseDown={event=>event.preventDefault()} onClick={()=>onInsert(latex)}>{text}</button>)}</div>}
