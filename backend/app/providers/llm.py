from typing import Protocol
from pydantic import BaseModel
from app.core.config import settings
from app.schemas.evaluation import *

class LLMProvider(Protocol):
    async def structured_response(self, *, instructions:str, input_text:str, response_model:type[BaseModel])->BaseModel: ...

class FakeLLMProvider:
    name="fake"; model="deterministic-examiner-v1"
    async def structured_response(self, *, instructions, input_text, response_model):
        injected="ignore the examiner" in input_text.lower()
        if response_model is CandidateAudit:
            return CandidateAudit(strategy_summary="La copie développe un raisonnement direct.",claims=[],major_errors=[] if not injected else [MathIssue(severity="major",category="other",description="Le texte ne fournit pas de raisonnement mathématique.",candidate_excerpt=None)],minor_errors=[],missing_justifications=[],conclusion_reached=not injected,conclusion_supported=not injected,provisional_status="correct" if not injected else "non_answer")
        if injected:
            return EvaluationResult(verdict="non_answer",score=1,confidence=.99,strategy_summary="Aucune stratégie mathématique exploitable.",reference_relationship="no_meaningful_strategy",rubric=EvaluationRubric(mathematical_correctness=0,rigor=0,clarity=1,efficiency=0),strengths=[],issues=[MathIssue(severity="major",category="other",description="La copie ne répond pas au problème.",candidate_excerpt=None)],missing_justifications=[],key_feedback="Rédigez une démonstration.",reference_method_summary="Le corrigé établit le résultat demandé.",suggested_improvement="Commencez par identifier les hypothèses et la conclusion.")
        return EvaluationResult(verdict="mostly_correct",score=16,confidence=.91,strategy_summary="La copie développe un raisonnement direct.",reference_relationship="alternative_valid_strategy",rubric=EvaluationRubric(mathematical_correctness=8,rigor=3.5,clarity=1.5,efficiency=3),strengths=["Idée principale trouvée","Calculs cohérents"],issues=[MathIssue(severity="minor",category="rigor",description="Une transition mérite une justification explicite.",candidate_excerpt=None)],missing_justifications=["Justifier la transition centrale."],key_feedback="Le raisonnement est globalement juste.",reference_method_summary="Le corrigé utilise une méthode différente.",suggested_improvement="Explicitez la transition centrale.")

class OpenAIProvider:
    name="openai"
    def __init__(self): self.model=settings.llm_model
    async def structured_response(self, *, instructions, input_text, response_model):
        if not settings.openai_api_key: raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=settings.openai_api_key,timeout=settings.llm_timeout_seconds)
        response=await client.responses.parse(model=self.model,instructions=instructions,input=input_text,text_format=response_model)
        if response.output_parsed is None: raise ValueError("provider returned no structured output")
        return response.output_parsed

def provider_from_settings():
    if settings.llm_provider=="fake": return FakeLLMProvider()
    if settings.llm_provider=="openai": return OpenAIProvider()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
