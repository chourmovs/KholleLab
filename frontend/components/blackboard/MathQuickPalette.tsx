"use client";
export const QUICK_KEYS = [
  ["=", "=", "Égal"], ["+", "+", "Plus"], ["−", "-", "Moins"], ["×", "\\times", "Multiplier"], ["÷", "\\div", "Diviser"],
  ["( )", "\\left(#0\\right)", "Parenthèses"], ["x²", "^{2}", "Carré"], ["xⁿ", "^{#0}", "Puissance"], ["√", "\\sqrt{#0}", "Racine carrée"], ["a/b", "\\frac{#0}{#?}", "Fraction"], ["|x|", "\\left|#0\\right|", "Valeur absolue"],
  ["≤", "\\le", "Inférieur ou égal"], ["≥", "\\ge", "Supérieur ou égal"], ["≠", "\\ne", "Différent"], ["⇒", "\\Rightarrow", "Implique"], ["⇔", "\\Leftrightarrow", "Équivaut"], ["π", "\\pi", "Pi"], ["∞", "\\infty", "Infini"], ["∑", "\\sum_{#0}^{#?}", "Somme"], ["∫", "\\int_{#0}^{#?}", "Intégrale"],
] as const;
export function MathQuickPalette({ onInsert }: { onInsert: (latex: string) => void }) { return <div className="quick-palette" aria-label="Symboles mathématiques rapides">{QUICK_KEYS.map(([text, latex, label]) => <button key={label} type="button" aria-label={label} onMouseDown={(event) => event.preventDefault()} onClick={() => onInsert(latex)}>{text}</button>)}</div>; }
