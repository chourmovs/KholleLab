"""Évaluation interactive, synchrone et sans accès au corrigé de référence."""
import json, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import component_logger
from app.models.attempt import Attempt, AttemptStatus
from app.models.tutor_assessment import TutorAssessmentRecord
from app.providers.llm import ModelRole, model_identity, resolve_model
from app.schemas.tutor import *
from app.domain.resource import ResourceType
from app.services.resource_resolver import ResourceContext

PROMPT=(Path(__file__).parents[1]/"prompts/tutor_assessment_v1.md").read_text(encoding="utf-8")
AUTO={TutorTrigger.MEANINGFUL_PROGRESS,TutorTrigger.STALLED}
GENERIC="Quelle étape de ton raisonnement peux-tu vérifier en priorité ?"
class TutorError(RuntimeError):
    def __init__(self,code,status=409): self.code,self.status=code,status; super().__init__(code)

VOCAB_LIMITS={"topics":8,"prerequisites":12,"skills":8,"tags":12}

def build_resource_vocabulary(problem,resources):
    """Return bounded semantic metadata; resource bodies and identities never leave the server."""
    eligible=[resource for resource in resources.list() if problem.curriculum.level in resource.curriculum_levels and (set(problem.topics)&set(resource.topics) or resource.id in problem.resource_refs)]
    def values(field):
        return sorted({getattr(value,"value",value) for resource in eligible for value in getattr(resource,field)})[:VOCAB_LIMITS[field]]
    return {"themes":values("topics"),"prerequis":values("prerequisites"),"competences":values("skills"),"tags":values("tags")}

def sanitize_resource_signal(signal:TutorResourceSignal,vocabulary:dict)->TutorResourceSignal:
    mapping={"topics":"themes","prerequisites":"prerequis","skills":"competences","tags":"tags"}
    update={field:[value for value in getattr(signal,field) if value in set(vocabulary[key])] for field,key in mapping.items()}
    return signal.model_copy(update=update)

def select_resource(problem,signal,safe,effective,trigger,resolver):
    if not settings.tutor_resource_recommendations_enabled or not signal.needed or safe.reveals_answer:
        return None
    automatic=trigger in AUTO
    threshold=settings.tutor_resource_auto_min_confidence if automatic else settings.tutor_resource_manual_min_confidence
    if safe.confidence<threshold or trigger==TutorTrigger.MEANINGFUL_PROGRESS:
        return None
    if not safe.intervention_needed and trigger!=TutorTrigger.STALLED:
        return None
    semantic=(*signal.topics,*signal.prerequisites,*signal.skills,*signal.tags)
    if not semantic and not problem.resource_refs:
        return None
    context=ResourceContext(curriculum_level=problem.curriculum.level,topics=tuple(signal.topics),prerequisites=tuple(signal.prerequisites),skills=tuple(signal.skills),tags=tuple(signal.tags),problem_id=problem.id,explicit_resource_refs=problem.resource_refs)
    candidates=resolver.resolve(context)
    if automatic:
        candidates=[item for item in candidates if item.resource.type==ResourceType.COURSE]
    elif trigger==TutorTrigger.ASK_HINT:
        if effective<=1:return None
        allowed={ResourceType.COURSE} if effective==2 else ({ResourceType.COURSE,ResourceType.EXAMPLE} if effective<4 else set(ResourceType))
        candidates=[item for item in candidates if item.resource.type in allowed]
    # Prefer a course on close scores, except when a worked example is explicitly diagnosed.
    if signal.need!=ResourceNeed.EXAMPLE_HELPFUL and candidates:
        best=candidates[0]
        courses=[item for item in candidates if item.resource.type==ResourceType.COURSE and item.score>=best.score-30]
        if courses:return courses[0]
    if signal.need==ResourceNeed.METHOD_GAP and trigger==TutorTrigger.I_AM_STUCK:
        examples=[item for item in candidates if item.resource.type==ResourceType.EXAMPLE]
        if examples and (not candidates or examples[0].score>=candidates[0].score-10):return examples[0]
    return candidates[0] if candidates else None

def apply_policy(a:TutorAssessment, requested:int, trigger:TutorTrigger)->tuple[TutorAssessment,int]:
    automatic=trigger in AUTO; allowed=min(requested,settings.tutor_auto_max_help_level) if automatic else requested
    if automatic and (a.reveals_answer or a.estimated_help_level>3): return a.model_copy(update={"intervention_needed":False,"intervention_type":InterventionType.SILENCE,"intervention":None}),0
    if a.reveals_answer and allowed<5: return a.model_copy(update={"intervention_needed":False,"intervention_type":InterventionType.SILENCE,"intervention":None}),0
    if a.confidence<.65:
        if automatic:return a.model_copy(update={"intervention_needed":False,"intervention_type":InterventionType.SILENCE,"intervention":None}),0
        return a.model_copy(update={"intervention_needed":True,"error_detected":False,"error_category":ErrorCategory.NONE,"intervention_type":InterventionType.SOCRATIC_QUESTION,"intervention":GENERIC,"reveals_answer":False}),1
    if a.confidence<.85 and a.intervention_needed:
        return a.model_copy(update={"error_detected":False,"error_category":ErrorCategory.NONE,"intervention_type":InterventionType.SOCRATIC_QUESTION,"intervention":GENERIC,"reveals_answer":False}),1
    effective=min(a.estimated_help_level,allowed)
    if not a.intervention_needed:return a.model_copy(update={"intervention_type":InterventionType.SILENCE,"intervention":None}),0
    if effective<a.estimated_help_level:
        return a.model_copy(update={"intervention_type":InterventionType.SOCRATIC_QUESTION,"intervention":GENERIC,"reveals_answer":False}),min(1,allowed)
    return a,effective

class TutorAssessmentService:
    def __init__(self,db:Session,problems,resources,resolver,provider): self.db,self.problems,self.resources,self.resolver,self.provider=db,problems,resources,resolver,provider
    async def assess(self,attempt_id:uuid.UUID,request:TutorRequest)->TutorResponse:
        if not settings.proactive_tutor_enabled: raise TutorError("tutor_disabled",503)
        attempt=self.db.get(Attempt,attempt_id)
        if not attempt: raise TutorError("attempt_not_found",404)
        if attempt.status!=AttemptStatus.DRAFT: raise TutorError("attempt_submitted")
        if attempt.revision!=request.expected_revision: raise TutorError("stale_revision")
        previous=self.db.scalar(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id==attempt_id,TutorAssessmentRecord.client_request_id==request.client_request_id))
        if previous:return self._public(previous)
        automatic=request.trigger in AUTO
        if automatic:
            count=self.db.scalar(select(func.count()).select_from(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id==attempt_id,TutorAssessmentRecord.trigger.in_([x.value for x in AUTO]))) or 0
            if count>=settings.tutor_max_auto_assessments_per_attempt: raise TutorError("tutor_auto_limit",429)
            latest=self.db.scalar(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id==attempt_id).order_by(TutorAssessmentRecord.created_at.desc()))
            if latest and (datetime.now(timezone.utc)-latest.created_at.replace(tzinfo=latest.created_at.tzinfo or timezone.utc)).total_seconds()<settings.tutor_min_assessment_interval_seconds: raise TutorError("tutor_cooldown",429)
        problem=self.problems.get(attempt.problem_id)
        # Intentionally enumerate safe fields: reference_solution can never enter this payload.
        vocabulary=build_resource_vocabulary(problem,self.resources)
        payload={"énoncé":problem.statement,"niveau":problem.curriculum.level.value,"difficulté":problem.curriculum.difficulty,"thèmes":[x.value for x in problem.topics],"prérequis":list(problem.prerequisites),"copie_enregistrée":attempt.solution_markdown,"temps_écoulé_secondes":attempt.elapsed_seconds,"niveau_aide_demandé":request.requested_help_level,"déclencheur":request.trigger.value,"vocabulaire_ressources_disponibles":vocabulary}
        model=resolve_model(settings.llm_model_family,ModelRole.FAST); short,backend=model_identity(model); started=time.perf_counter()
        component_logger("tutor").bind(attempt_id=str(attempt_id),revision=attempt.revision,trigger=request.trigger.value,requested_help_level=request.requested_help_level,model=model,provider=getattr(self.provider,"name","unknown")).info("tutor_assessment_started")
        raw=await self.provider.structured_response(instructions=PROMPT,input_text=json.dumps(payload,ensure_ascii=False),response_model=TutorAssessment,role=ModelRole.FAST)
        safe,effective=apply_policy(raw,request.requested_help_level,request.trigger)
        signal=sanitize_resource_signal(safe.resource_signal,vocabulary)
        discarded=sum(len(getattr(safe.resource_signal,key))-len(getattr(signal,key)) for key in ("topics","prerequisites","skills","tags"))
        if discarded:component_logger("tutor").bind(discarded_resource_signal_values=discarded).warning("tutor_resource_signal_sanitized")
        selected=None if raw.reveals_answer else select_resource(problem,signal,safe,effective,request.trigger,self.resolver)
        row=TutorAssessmentRecord(attempt_id=attempt_id,revision=attempt.revision,trigger=request.trigger.value,requested_help_level=request.requested_help_level,effective_help_level=effective,student_state=safe.student_state.value,intervention_needed=safe.intervention_needed,intervention_type=safe.intervention_type.value,intervention=safe.intervention,confidence=safe.confidence,error_category=safe.error_category.value,reveals_answer=safe.reveals_answer,provider=getattr(self.provider,"name","unknown"),model=short,backend=backend,client_request_id=request.client_request_id,recommended_resource_id=selected.resource.id if selected else None,resource_need=signal.need.value if selected else None)
        self.db.add(row);self.db.commit();self.db.refresh(row)
        component_logger("tutor").bind(attempt_id=str(attempt_id),revision=attempt.revision,student_state=row.student_state,intervention_needed=row.intervention_needed,effective_help_level=effective,confidence=row.confidence,latency_ms=round((time.perf_counter()-started)*1000,1)).info("tutor_assessment_completed")
        return self._public(row)
    def latest(self,attempt_id):
        row=self.db.scalar(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id==attempt_id).order_by(TutorAssessmentRecord.created_at.desc()))
        return self._public(row) if row else None
    def _public(self,r):
        resource=self.resources.get(r.recommended_resource_id) if r.recommended_resource_id else None
        recommendation=TutorResourceRecommendation(id=resource.id,type=resource.type,title=resource.title,need=r.resource_need) if resource and r.resource_need else None
        return TutorResponse(assessment_id=str(r.id),revision=r.revision,student_state=r.student_state,intervention_needed=r.intervention_needed,intervention_type=r.intervention_type,intervention=r.intervention,confidence=r.confidence,effective_help_level=r.effective_help_level,provider=r.provider,model=r.model,backend=r.backend,resource_recommendation=recommendation)
