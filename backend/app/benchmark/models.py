"""Versioned data contracts and loader for the pedagogical benchmark."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field, model_validator

class CurriculumLevel(str,Enum):
    SECONDE="seconde"; PREMIERE="premiere"; TERMINALE="terminale"; MATHS_SUP="maths-sup"; MATHS_SPE="maths-spe"
class TaskType(str,Enum):
    VALID_PROGRESS="valid_progress"; MATHEMATICAL_ERROR="mathematical_error"; MISSING_JUSTIFICATION="missing_justification"; STUDENT_BLOCKED="student_blocked"; COURSE_GAP="course_gap"; WRONG_STRATEGY="wrong_strategy"; ALTERNATIVE_VALID_METHOD="alternative_valid_method"; FALSE_CLAIM="false_claim"; ALMOST_COMPLETE="almost_complete"; PROMPT_INJECTION="prompt_injection"
class StudentState(str,Enum):
    PROGRESSING="progressing"; BLOCKED="blocked"; ERROR="error"; MISSING_JUSTIFICATION="missing_justification"; COMPLETE="complete"
class ErrorCategory(str,Enum):
    NONE="none"; ALGEBRA="algebra"; CALCULATION="calculation"; LOGIC="logic"; DOMAIN="domain"; THEOREM="theorem"; RIGOR="rigor"; STRATEGY="strategy"; OTHER="other"
class InterventionType(str,Enum):
    SILENCE="silence"; ENCOURAGEMENT="encouragement"; SOCRATIC_QUESTION="socratic_question"; DIRECTION="direction"; COURSE_REMINDER="course_reminder"; HINT="hint"; CORRECTION="correction"
class TutorAssessment(BaseModel):
    student_state:StudentState; intervention_needed:bool; error_detected:bool; error_category:ErrorCategory
    confidence:float=Field(ge=0,le=1); intervention_type:InterventionType; intervention:str|None=None
    reveals_answer:bool=False; estimated_help_level:int=Field(ge=0,le=5)
    @model_validator(mode="after")
    def consistent(self):
        if self.intervention_needed and not (self.intervention or "").strip(): raise ValueError("an intervention is required")
        if self.intervention_type==InterventionType.SILENCE and self.intervention: raise ValueError("silence cannot contain intervention text")
        return self
class Curriculum(BaseModel): level:CurriculumLevel; difficulty:int=Field(ge=1,le=5); topic:str
class Problem(BaseModel): statement:str=Field(min_length=1)
class StudentWork(BaseModel): solution:str
class Expected(BaseModel):
    state:StudentState; error_present:bool; error_category:ErrorCategory; intervention_type:InterventionType; intervention_needed:bool
class Forbidden(BaseModel): reveal_final_answer:bool=True; forbidden_answers:list[str]=Field(default_factory=list); expected_final_answer_latex:str|None=None
class Reference(BaseModel): error_description:str|None=None; acceptable_interventions:list[str]=Field(default_factory=list)
class BenchmarkCase(BaseModel):
    id:str=Field(pattern=r"^[a-z0-9-]+$"); task_type:TaskType; quick:bool=False; curriculum:Curriculum; problem:Problem
    student_state:StudentWork; requested_help_level:int=Field(ge=0,le=5); expected:Expected; forbidden:Forbidden=Field(default_factory=Forbidden); reference:Reference=Field(default_factory=Reference)
    @model_validator(mode="after")
    def nonempty_work(self):
        if not self.student_state.solution.strip() and self.task_type!=TaskType.STUDENT_BLOCKED: raise ValueError("student solution is empty")
        if any(not x.strip() for x in self.forbidden.forbidden_answers): raise ValueError("empty forbidden answer")
        return self

def load_cases(root:Path)->list[BenchmarkCase]:
    cases=[]
    for path in sorted(root.glob("**/*.y*ml")):
        raw=yaml.safe_load(path.read_text(encoding="utf-8")); docs=raw if isinstance(raw,list) else [raw]
        cases.extend(BenchmarkCase.model_validate(x) for x in docs)
    ids=[x.id for x in cases]
    dupes=sorted({x for x in ids if ids.count(x)>1})
    if dupes: raise ValueError(f"duplicate benchmark IDs: {', '.join(dupes)}")
    return cases
