import type { ProblemSource } from "@/lib/types";
export function SourceBadge({source,year}:{source:ProblemSource;year?:number}){return <span className="source">{source.name}{year||source.year?` — ${year??source.year}`:""}</span>}
