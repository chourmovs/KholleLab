import type {ProgressionSummary} from "@/lib/types";
export function PracticeSummary({progression,error}:{progression?:ProgressionSummary;error:boolean}){
 return <section className="landing-section practice-summary" aria-labelledby="practice-title"><p className="eyebrow">Régularité</p><h2 id="practice-title">Ma pratique</h2>{progression?<dl><div><dt>Expérience</dt><dd>{progression.total_xp} XP</dd></div><div><dt>Série actuelle</dt><dd>🔥 {progression.current_streak_days} jour{progression.current_streak_days>1?"s":""}</dd></div><div><dt>Aujourd’hui</dt><dd>{progression.today_xp} / {progression.daily_goal_xp} XP</dd></div></dl>:<p className="muted-state">{error?"Les statistiques de pratique sont momentanément indisponibles.":"Pas encore de statistiques de pratique."}</p>}</section>
}
