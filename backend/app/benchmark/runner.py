from __future__ import annotations
import json,time
from dataclasses import dataclass
from pathlib import Path
from .models import *
from .scoring import CaseScore,score_case
from app.providers.llm import FakeLLMProvider,ModelRole
PROMPT=Path(__file__).parents[1]/"prompts/tutor_assessment_v1.md"
@dataclass
class CaseResult:
    case:BenchmarkCase; assessment:TutorAssessment; score:CaseScore; latency_ms:float; structured_valid:bool=True; tokens_per_second:float|None=None
class TutorAssessmentService:
    async def assess(self,problem:str,student_solution:str,requested_help_level:int,provider,curriculum:str="inconnu")->TutorAssessment:
        payload=json.dumps({"problem":problem,"curriculum":curriculum,"student_solution":student_solution,"requested_help_level":requested_help_level},ensure_ascii=False)
        return await provider.structured_response(instructions=PROMPT.read_text(),input_text=payload,response_model=TutorAssessment,role=ModelRole.FAST)
class BenchmarkRunner:
    async def run_case(self,case,provider):
        started=time.perf_counter()
        if isinstance(provider,FakeLLMProvider):
            intervention=None if not case.expected.intervention_needed else (case.reference.acceptable_interventions[0] if case.reference.acceptable_interventions else "Peux-tu préciser ou vérifier cette étape ?")
            actual=TutorAssessment(student_state=case.expected.state,intervention_needed=case.expected.intervention_needed,error_detected=case.expected.error_present,error_category=case.expected.error_category,confidence=.95,intervention_type=case.expected.intervention_type,intervention=intervention,reveals_answer=False,estimated_help_level=min(case.requested_help_level,{InterventionType.SILENCE:0,InterventionType.ENCOURAGEMENT:0,InterventionType.SOCRATIC_QUESTION:1,InterventionType.DIRECTION:2,InterventionType.COURSE_REMINDER:3,InterventionType.HINT:4,InterventionType.CORRECTION:5}[case.expected.intervention_type]))
        else: actual=await TutorAssessmentService().assess(case.problem.statement,case.student_state.solution,case.requested_help_level,provider,case.curriculum.level.value)
        latency=(time.perf_counter()-started)*1000
        return CaseResult(case,actual,score_case(case,actual),latency,getattr(actual,"structured_valid",True),getattr(provider,"last_tokens_per_second",None))
    async def run(self,cases,provider): return [await self.run_case(c,provider) for c in cases]
