"""Contrat de production du colleur automatique."""
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.domain.resource import ResourceType

SlugSignal = str

class StudentState(StrEnum):
    PROGRESSING="progressing"; BLOCKED="blocked"; ERROR="error"; MISSING_JUSTIFICATION="missing_justification"; COMPLETE="complete"
class ErrorCategory(StrEnum):
    NONE="none"; ALGEBRA="algebra"; CALCULATION="calculation"; LOGIC="logic"; DOMAIN="domain"; THEOREM="theorem"; RIGOR="rigor"; STRATEGY="strategy"; OTHER="other"
class InterventionType(StrEnum):
    SILENCE="silence"; ENCOURAGEMENT="encouragement"; SOCRATIC_QUESTION="socratic_question"; DIRECTION="direction"; COURSE_REMINDER="course_reminder"; HINT="hint"; CORRECTION="correction"
class TutorTrigger(StrEnum):
    MEANINGFUL_PROGRESS="meaningful_progress"; STALLED="stalled"; ASK_HINT="ask_hint"; I_AM_STUCK="i_am_stuck"

class ResourceNeed(StrEnum):
    NONE="none"; COURSE_GAP="course_gap"; METHOD_GAP="method_gap"; EXAMPLE_HELPFUL="example_helpful"

class TutorResourceSignal(BaseModel):
    model_config=ConfigDict(extra="forbid")
    needed:bool=False; need:ResourceNeed=ResourceNeed.NONE
    topics:list[SlugSignal]=Field(default_factory=list,max_length=3)
    prerequisites:list[SlugSignal]=Field(default_factory=list,max_length=3)
    skills:list[SlugSignal]=Field(default_factory=list,max_length=2)
    tags:list[SlugSignal]=Field(default_factory=list,max_length=3)
    @model_validator(mode="after")
    def consistent(self):
        values=(*self.topics,*self.prerequisites,*self.skills,*self.tags)
        if any(not value or len(value)>64 or not value.replace("-","").isalnum() or value.lower()!=value for value in values):
            raise ValueError("resource vocabulary values must be compact slugs")
        if not self.needed and (self.need!=ResourceNeed.NONE or values):
            raise ValueError("an unneeded resource signal must be empty")
        if self.needed and self.need==ResourceNeed.NONE:
            raise ValueError("a needed resource signal requires a need")
        return self

class TutorAssessment(BaseModel):
    student_state:StudentState; intervention_needed:bool; error_detected:bool; error_category:ErrorCategory
    confidence:float=Field(ge=0,le=1); intervention_type:InterventionType; intervention:str|None=None
    reveals_answer:bool=False; estimated_help_level:int=Field(ge=0,le=5)
    resource_signal:TutorResourceSignal=Field(default_factory=TutorResourceSignal)
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
    resource_recommendation:"TutorResourceRecommendation | None"=None

class TutorResourceRecommendation(BaseModel):
    id:str; type:ResourceType; title:str; need:ResourceNeed
