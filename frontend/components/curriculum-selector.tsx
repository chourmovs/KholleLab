import type {CurriculumMetadata} from "@/lib/types";

const STAGES: {id:"college"|"lycee"|"cpge";label:string}[] = [
  {id:"college",label:"Collège"},{id:"lycee",label:"Lycée"},{id:"cpge",label:"Prépa"},
];

export function CurriculumSelector({metadata,level,difficulty,domain,expectation,onLevel,onDifficulty,onDomain,onExpectation}:{metadata:CurriculumMetadata;level:string;difficulty:number;domain:string;expectation:string;onLevel:(v:string)=>void;onDifficulty:(v:number)=>void;onDomain:(v:string)=>void;onExpectation:(v:string)=>void}){
  const current=metadata.levels.find(item=>item.id===level);
  const domains=current?.domains??[];
  const objectives=domains.find(item=>item.id===domain)?.expectations??[];
  return <section className="curriculum-selector">
    <label>Niveau <select aria-label="Niveau" value={level} onChange={event=>onLevel(event.target.value)}>{STAGES.map(stage=><optgroup key={stage.id} label={stage.label}>{metadata.levels.filter(item=>item.stage===stage.id).map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</optgroup>)}</select></label>
    <label>Domaine <select aria-label="Domaine" value={domain} onChange={event=>onDomain(event.target.value)}><option value="">Tous les domaines</option>{domains.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <label>Objectif précis <select aria-label="Objectif précis" value={expectation} disabled={!domain} onChange={event=>onExpectation(event.target.value)}><option value="">Tous les objectifs</option>{objectives.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    <fieldset><legend>Intensité</legend>{metadata.difficulties.map(item=><button type="button" className={difficulty===item.id?"active":""} key={item.id} title={item.label} aria-label={`${item.id} ${item.label}`} onClick={()=>onDifficulty(item.id)}>{item.id}</button>)}</fieldset>
  </section>
}
