"use client";
import katex from "katex";
export function ProblemPanel() {
  const formula = katex.renderToString("f(x)=x+\\frac{1}{x}\\geq 2", { throwOnError: false, displayMode: true });
  return <section className="panel problem"><div className="eyebrow">01 — Énoncé</div><h1>Une inégalité élémentaire</h1><p>Montrer que, pour tout <em>x &gt; 0</em> :</p><div className="formula" dangerouslySetInnerHTML={{ __html: formula }} /><p className="aside">Un premier exercice pour prendre place au tableau. La résolution interactive arrivera prochainement.</p></section>;
}
