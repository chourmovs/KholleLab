import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import httpx
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

class InferenceProfile(str, Enum):
    FAST = "fast"
    DEEP = "deep"

@dataclass(frozen=True)
class GenerationSettings:
    temperature: float
    top_p: float
    max_tokens: int

PROFILE_SETTINGS = {
    InferenceProfile.FAST: GenerationSettings(temperature=.2, top_p=.9, max_tokens=192),
    InferenceProfile.DEEP: GenerationSettings(temperature=.1, top_p=.95, max_tokens=768),
}

class LocalLLMError(RuntimeError):
    """A controlled local inference failure."""

class LocalLLMProvider:
    name = "local"

    def __init__(self, *, client: httpx.AsyncClient | None = None):
        if not settings.local_llm_base_url.startswith(("http://", "https://")):
            raise RuntimeError("LOCAL_LLM_BASE_URL must be an HTTP(S) URL")
        if not settings.local_llm_model.strip():
            raise RuntimeError("LOCAL_LLM_MODEL must not be empty")
        self.model = settings.local_llm_model
        self._client = client
        self.last_latency_ms: float | None = None

    async def structured_response(self, *, instructions, input_text, response_model, profile=InferenceProfile.DEEP):
        generation = PROFILE_SETTINGS[InferenceProfile(profile)]
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            "temperature": generation.temperature,
            "top_p": generation.top_p,
            "max_tokens": generation.max_tokens,
            "response_format": {"type": "json_object"},
        }
        owned = self._client is None
        client = self._client or httpx.AsyncClient(timeout=settings.local_llm_timeout_seconds)
        started = time.perf_counter()
        try:
            response = await client.post(f"{settings.local_llm_base_url.rstrip('/')}/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
            choices = body.get("choices")
            if not choices:
                raise LocalLLMError("local inference returned no choices")
            content = choices[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise LocalLLMError("local inference returned empty content")
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0]
            return response_model.model_validate(json.loads(clean))
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise LocalLLMError(f"local inference unavailable: {type(exc).__name__}") from exc
        except httpx.HTTPStatusError as exc:
            raise LocalLLMError(f"local inference HTTP {exc.response.status_code}") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise LocalLLMError("local inference returned a malformed response") from exc
        finally:
            self.last_latency_ms = (time.perf_counter() - started) * 1000
            if owned:
                await client.aclose()

def provider_from_settings():
    if settings.llm_provider=="fake": return FakeLLMProvider()
    if settings.llm_provider=="openai": return OpenAIProvider()
    if settings.llm_provider=="local": return LocalLLMProvider()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
