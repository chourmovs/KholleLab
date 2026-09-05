"""Contrat de production du colleur automatique."""
from enum import StrEnum
from pydantic import BaseModel, Field, model_validator

class StudentState(StrEnum):
    PROGRESSING="progressing"; BLOCKED="blocked"; ERROR="error"; MISSING_JUSTIFICATION="missing_justification"; COMPLETE="complete"
class ErrorCategory(StrEnum):
    NONE="none"; ALGEBRA="algebra"; CALCULATION="calculation"; LOGIC="logic"; DOMAIN="domain"; THEOREM="theorem"; RIGOR="rigor"; STRATEGY="strategy"; OTHER="other"
class InterventionType(StrEnum):
    SILENCE="silence"; ENCOURAGEMENT="encouragement"; SOCRATIC_QUESTION="socratic_question"; DIRECTION="direction"; COURSE_REMINDER="course_reminder"; HINT="hint"; CORRECTION="correction"
class TutorTrigger(StrEnum):
    MEANINGFUL_PROGRESS="meaningful_progress"; STALLED="stalled"; ASK_HINT="ask_hint"; I_AM_STUCK="i_am_stuck"

class TutorAssessment(BaseModel):
    student_state:StudentState; intervention_needed:bool; error_detected:bool; error_category:ErrorCategory
    confidence:float=Field(ge=0,le=1); intervention_type:InterventionType; intervention:str|None=None
    reveals_answer:bool=False; estimated_help_level:int=Field(ge=0,le=5)
    @model_validator(mode="after")
    def consistent(self):
        if self.intervention_needed and not (self.intervention or "").strip(): raise ValueError("an intervention is required")
        if self.intervention_type==InterventionType.SILENCE and self.intervention: raise ValueError("silence cannot contain intervention text")
        return self

class TutorRequest(BaseModel):
    expected_revision:int=Field(ge=0); trigger:TutorTrigger; requested_help_level:int=Field(ge=0,le=5); client_request_id:str=Field(min_length=1,max_length=100)

class TutorResponse(BaseModel):
    status:str="completed"; assessment_id:str; revision:int; student_state:StudentState
    intervention_needed:bool; intervention_type:InterventionType; intervention:str|None; confidence:float
    effective_help_level:int; provider:str; model:str; backend:str
