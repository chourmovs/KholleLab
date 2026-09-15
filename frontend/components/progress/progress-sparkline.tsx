import type {CurriculumProgressHistory} from "@/lib/types";

export function ProgressSparkline({history,currentSolved,currentPercent}:{history?:CurriculumProgressHistory;currentSolved:number;currentPercent:number}){
 if(!history)return <p className="curve-unavailable">Courbe momentanément indisponible.</p>;
 if(!history.points.length)return <p className="curve-empty">Ta courbe commencera avec ton premier acquis validé.</p>;
 const width=300,height=92,pad=8;
 const values=history.points.map(point=>point.progress_percent);
 const x=(index:number)=>values.length===1?width/2:pad+index*(width-pad*2)/(values.length-1);
 const y=(value:number)=>height-pad-(Math.max(0,Math.min(100,value))/100)*(height-pad*2);
 const path=values.map((value,index)=>`${index?"L":"M"} ${x(index)} ${y(value)}`).join(" ");
 return <figure className="progress-curve"><figcaption>Évolution récente · {currentSolved} sur {history.eligible} acquis, {Math.round(currentPercent)} % du niveau validé</figcaption><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-hidden="true"><line className="unlock-line" x1={pad} x2={width-pad} y1={y(60)} y2={y(60)}/><text x={pad} y={y(60)-4}>60 %</text><path d={path}/><circle cx={x(values.length-1)} cy={y(values.at(-1)!)} r="4"/></svg></figure>
}
