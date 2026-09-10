import type { ProblemSource } from "@/lib/types";
export function SourceBadge({source,year}:{source:ProblemSource;year?:number}){const name=source.name==="Khollelab deterministic corpus factory"?"Exercice généré par KHOLLELAB":source.name;return <span className="source">{name}{year||source.year?` — ${year??source.year}`:""}</span>}
