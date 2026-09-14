"use client";

import {useCallback,useEffect,useState} from "react";
import {ArrowLeft,Flame,RefreshCw,Target,Trophy,UserRound} from "lucide-react";
import {getLearnerProfile,getProgression} from "@/lib/api";
import type {KnowledgeMasterySummary,LearnerProfile,MasteryState,PracticeMilestone,ProgressionSummary} from "@/lib/types";

const stateLabels:Record<MasteryState,string>={not_enough_data:"Pas assez de données",emerging:"En découverte",practicing:"En consolidation",established:"Bien établi"};
const reasonLabels:Record<string,string>={repeated_negative:"Plusieurs réponses incorrectes récentes",partial_results:"Résultats partiels à consolider",course_gap:"Rappel de cours utile",method_gap:"Méthode encore à consolider",incomplete_work:"Travail récent resté incomplet",prerequisite_gap:"Prérequis immédiat à consolider",inconsistent_results:"Résultats récents encore irréguliers"};
const shortDate=(value:string)=>new Intl.DateTimeFormat("fr-FR",{day:"numeric",month:"short"}).format(new Date(value));
type LoadState="loading"|"ready"|"error";

function Area({item}:{item:KnowledgeMasterySummary}) {
  return <article className={`profile-area ${item.state}`}><header><h3>{item.label}</h3><span>{stateLabels[item.state]}</span></header><p>{item.evidence_count} séance{item.evidence_count>1?"s":""} · difficulté {item.difficulty_min===item.difficulty_max?item.difficulty_min:`${item.difficulty_min}–${item.difficulty_max}`}</p><small>Dernière pratique : {shortDate(item.last_practiced_at)}</small></article>;
}

export function LearnerProfileView({onClose}:{onClose:()=>void}) {
  const[profile,setProfile]=useState<LearnerProfile>();
  const[progression,setProgression]=useState<ProgressionSummary>();
  const[masteryState,setMasteryState]=useState<LoadState>("loading");
  const[progressionState,setProgressionState]=useState<LoadState>("loading");
  const loadMastery=useCallback(async()=>{setMasteryState("loading");try{setProfile(await getLearnerProfile());setMasteryState("ready")}catch{setMasteryState("error")}},[]);
  const loadProgression=useCallback(async()=>{setProgressionState("loading");try{setProgression(await getProgression());setProgressionState("ready")}catch{setProgressionState("error")}},[]);
  useEffect(()=>{
    let active=true;
    void getLearnerProfile().then(value=>{if(active){setProfile(value);setMasteryState("ready")}}).catch(()=>{if(active)setMasteryState("error")});
    void getProgression().then(value=>{if(active){setProgression(value);setProgressionState("ready")}}).catch(()=>{if(active)setProgressionState("error")});
    return()=>{active=false};
  },[]);
  const bothFailed=masteryState==="error"&&progressionState==="error";
  return <section className="profile-view">
    <header className="profile-title"><button className="history-back" onClick={onClose}><ArrowLeft/> Retour à l’espace de travail</button><h1><UserRound/> Profil d’apprentissage</h1><p>La progression mesure la pratique régulière ; la maîtrise mathématique repose séparément sur les résultats évalués.</p></header>
    {bothFailed?<div className="profile-state" role="alert">Impossible de charger le profil.<button onClick={()=>{void loadMastery();void loadProgression()}}><RefreshCw/> Réessayer</button></div>:<div className="profile-content">
      {progressionState==="loading"?<SectionLoading label="Chargement de la progression…"/>:progressionState==="error"?<section className="progression-section" aria-labelledby="progression-title"><h2 id="progression-title">Progression</h2><p role="status">Progression temporairement indisponible.</p></section>:progression&&<ProgressionSection progression={progression}/>}
      {masteryState==="loading"?<SectionLoading label="Chargement de la maîtrise…"/>:masteryState==="error"?<section className="mastery-section" aria-labelledby="mastery-title"><h2 id="mastery-title">Maîtrise mathématique</h2><p role="alert">La maîtrise mathématique est temporairement indisponible.</p><button onClick={()=>void loadMastery()}><RefreshCw/> Réessayer</button></section>:profile&&<MasteryContent profile={profile}/>}
    </div>}
  </section>;
}

function SectionLoading({label}:{label:string}) {return <p className="profile-state" aria-live="polite">{label}</p>}

function milestoneValue(item:PracticeMilestone) {return `${item.current} / ${item.target}${item.kind==="xp"?" XP":item.kind==="streak"?" jours":" exercices"}`}

function ProgressionSection({progression}:{progression:ProgressionSummary}) {
  const range=progression.next_rank_xp-progression.current_rank_start_xp;
  const gradeProgress=range?Math.max(0,Math.min(100,(progression.total_xp-progression.current_rank_start_xp)/range*100)):0;
  const goalProgress=Math.max(0,Math.min(100,progression.today_xp/progression.daily_goal_xp*100));
  const unlocked=progression.milestones.filter(item=>item.unlocked);
  const next=progression.milestones.find(item=>!item.unlocked);
  return <section className="progression-section" aria-labelledby="progression-title">
    <h2 id="progression-title">Progression</h2>
    <div className="progression-stats"><strong>Rang XP {progression.xp_rank}</strong><span>{progression.total_xp} XP</span><span><Flame aria-hidden="true"/> Série actuelle : {progression.current_streak_days} jour{progression.current_streak_days>1?"s":""}</span><span>Record : {progression.longest_streak_days} jour{progression.longest_streak_days>1?"s":""}</span></div>
    <div className="rank-progress" role="progressbar" aria-label="Progression vers le prochain rang XP" aria-valuemin={progression.current_rank_start_xp} aria-valuemax={progression.next_rank_xp} aria-valuenow={progression.total_xp}><span style={{width:`${gradeProgress}%`}}/></div><p>{progression.xp_to_next_rank} XP avant le rang XP {progression.xp_rank+1}</p>
    <div className="daily-goal"><h3><Target aria-hidden="true"/> Aujourd’hui</h3><strong>{progression.today_xp} / {progression.daily_goal_xp} XP</strong><div className="daily-goal-progress" role="progressbar" aria-label="Objectif de pratique du jour" aria-valuemin={0} aria-valuemax={progression.daily_goal_xp} aria-valuenow={Math.min(progression.today_xp,progression.daily_goal_xp)}><span style={{width:`${goalProgress}%`}}/></div><p>{progression.daily_goal_completed?"Objectif du jour atteint ✓":`Encore ${Math.max(0,progression.daily_goal_xp-progression.today_xp)} XP pour l’objectif du jour`}</p></div>
    <div className="milestones"><h3><Trophy aria-hidden="true"/> Étapes franchies</h3>{unlocked.length?<ul>{unlocked.map(item=><li key={item.id}><Trophy aria-hidden="true"/><span>{item.label}</span></li>)}</ul>:<p>La première étape viendra avec un exercice terminé.</p>}{next&&<div className="next-milestone"><strong>Prochaine étape</strong><span>{next.label}</span><small>{milestoneValue(next)}</small></div>}</div>
  </section>;
}

function MasteryContent({profile}:{profile:LearnerProfile}) {
  const a=profile.activity;
  const grouped=profile.knowledge.reduce<Record<string,KnowledgeMasterySummary[]>>((result,node)=>{(result[node.parent_label??"Autres notions"]??=[]).push(node);return result},{});
  return <>
    <section aria-labelledby="activity-title"><h2 id="activity-title">Activité récente</h2><p className="activity-line"><strong>{a.sessions_total}</strong> séances · <strong>{a.sessions_completed}</strong> terminées · <strong>{a.sessions_abandoned}</strong> abandonnées · <strong>{a.attempts_total}</strong> tentatives</p><p>{a.sessions_last_30_days} séance{a.sessions_last_30_days>1?"s":""} ces 30 derniers jours</p></section>
    <section className="mastery-section" aria-labelledby="mastery-title"><h2 id="mastery-title">Maîtrise mathématique</h2><p>La maîtrise par notion est indépendante des XP, du rang XP et des séries.</p>{profile.knowledge.length===0?<div className="profile-empty"><h3>Pas encore assez de séances pour établir une maîtrise.</h3><p>Cette synthèse se précisera avec des travaux évalués.</p></div>:Object.entries(grouped).map(([domain,nodes])=><section key={domain} className="knowledge-domain"><h3>{domain}</h3><div className="profile-grid">{nodes.map(item=><Area key={item.identifier} item={item}/>)}</div></section>)}</section>
    {profile.needs_consolidation.length>0&&<section><h2>À consolider</h2><div className="consolidation-list">{profile.needs_consolidation.map(item=><article key={`${item.kind}-${item.identifier}`}><h3>{item.label}</h3>{item.reasons.map(reason=><p key={reason}>{reasonLabels[reason]??reason}</p>)}{item.prerequisites?.map(prerequisite=><p key={prerequisite.identifier}>{prerequisite.status==="not_practiced"?`${prerequisite.label} n’a pas encore été suffisamment travaillé.`:`${prerequisite.label} à consolider avant ${item.label.toLocaleLowerCase("fr-FR")}.`}</p>)}</article>)}</div></section>}
    {profile.strengths.length>0&&<section><h2>Points bien établis dans les séances récentes</h2><div className="profile-grid">{profile.strengths.map(item=><Area key={item.identifier} item={item}/>)}</div></section>}
  </>;
}
