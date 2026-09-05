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

PROMPT=(Path(__file__).parents[1]/"prompts/tutor_assessment_v1.md").read_text(encoding="utf-8")
AUTO={TutorTrigger.MEANINGFUL_PROGRESS,TutorTrigger.STALLED}
GENERIC="Quelle étape de ton raisonnement peux-tu vérifier en priorité ?"
class TutorError(RuntimeError):
    def __init__(self,code,status=409): self.code,self.status=code,status; super().__init__(code)

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
    def __init__(self,db:Session,problems,provider): self.db,self.problems,self.provider=db,problems,provider
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
        payload={"énoncé":problem.statement,"niveau":problem.curriculum.level.value,"difficulté":problem.curriculum.difficulty,"thèmes":[x.value for x in problem.topics],"prérequis":list(problem.prerequisites),"copie_enregistrée":attempt.solution_markdown,"temps_écoulé_secondes":attempt.elapsed_seconds,"niveau_aide_demandé":request.requested_help_level,"déclencheur":request.trigger.value}
        model=resolve_model(settings.llm_model_family,ModelRole.FAST); short,backend=model_identity(model); started=time.perf_counter()
        component_logger("tutor").bind(attempt_id=str(attempt_id),revision=attempt.revision,trigger=request.trigger.value,requested_help_level=request.requested_help_level,model=model,provider=getattr(self.provider,"name","unknown")).info("tutor_assessment_started")
        raw=await self.provider.structured_response(instructions=PROMPT,input_text=json.dumps(payload,ensure_ascii=False),response_model=TutorAssessment,role=ModelRole.FAST)
        safe,effective=apply_policy(raw,request.requested_help_level,request.trigger)
        row=TutorAssessmentRecord(attempt_id=attempt_id,revision=attempt.revision,trigger=request.trigger.value,requested_help_level=request.requested_help_level,effective_help_level=effective,student_state=safe.student_state.value,intervention_needed=safe.intervention_needed,intervention_type=safe.intervention_type.value,intervention=safe.intervention,confidence=safe.confidence,error_category=safe.error_category.value,reveals_answer=safe.reveals_answer,provider=getattr(self.provider,"name","unknown"),model=short,backend=backend,client_request_id=request.client_request_id)
        self.db.add(row);self.db.commit();self.db.refresh(row)
        component_logger("tutor").bind(attempt_id=str(attempt_id),revision=attempt.revision,student_state=row.student_state,intervention_needed=row.intervention_needed,effective_help_level=effective,confidence=row.confidence,latency_ms=round((time.perf_counter()-started)*1000,1)).info("tutor_assessment_completed")
        return self._public(row)
    def latest(self,attempt_id):
        row=self.db.scalar(select(TutorAssessmentRecord).where(TutorAssessmentRecord.attempt_id==attempt_id).order_by(TutorAssessmentRecord.created_at.desc()))
        return self._public(row) if row else None
    @staticmethod
    def _public(r): return TutorResponse(assessment_id=str(r.id),revision=r.revision,student_state=r.student_state,intervention_needed=r.intervention_needed,intervention_type=r.intervention_type,intervention=r.intervention,confidence=r.confidence,effective_help_level=r.effective_help_level,provider=r.provider,model=r.model,backend=r.backend)
