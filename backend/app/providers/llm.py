import json
import random
import time
from enum import Enum
from typing import Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from app.core.config import ModelFamily, settings
from app.core.logging import component_logger
from app.schemas.evaluation import *


class ModelRole(str, Enum):
    FAST = "fast"
    DEEP = "deep"


def resolve_model(family: ModelFamily | str, role: ModelRole | str) -> str:
    family, role = ModelFamily(family), ModelRole(role)
    return {
        (ModelFamily.QWEN, ModelRole.FAST): settings.hf_qwen_fast_model,
        (ModelFamily.QWEN, ModelRole.DEEP): settings.hf_qwen_deep_model,
        (ModelFamily.GEMMA, ModelRole.FAST): settings.hf_gemma_fast_model,
        (ModelFamily.GEMMA, ModelRole.DEEP): settings.hf_gemma_deep_model,
    }[(family, role)]


def model_identity(model: str) -> tuple[str, str]:
    raw, _, backend = model.partition(":")
    return raw.rsplit("/", 1)[-1].replace("-it", ""), backend or "auto"


class LLMProvider(Protocol):
    async def structured_response(self, *, instructions: str, input_text: str,
                                  response_model: type[BaseModel], role: ModelRole = ModelRole.DEEP,
                                  family: ModelFamily | None = None) -> BaseModel: ...


class RemoteLLMError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int | None = None):
        self.code, self.status = code, status
        super().__init__(message)


class FakeLLMProvider:
    name="fake"; model="deterministic-examiner-v1"
    async def structured_response(self, *, instructions, input_text, response_model, **_):
        injected="ignore the examiner" in input_text.lower()
        if response_model is CandidateAudit:
            return CandidateAudit(strategy_summary="La copie développe un raisonnement direct.",claims=[],major_errors=[] if not injected else [MathIssue(severity="major",category="other",description="Le texte ne fournit pas de raisonnement mathématique.",candidate_excerpt=None)],minor_errors=[],missing_justifications=[],conclusion_reached=not injected,conclusion_supported=not injected,provisional_status="correct" if not injected else "non_answer")
        if response_model.__name__ == "TutorAssessment":
            return response_model(student_state="progressing",intervention_needed=False,error_detected=False,error_category="none",confidence=.9,intervention_type="silence",intervention=None,reveals_answer=False,estimated_help_level=0)
        if injected:
            return EvaluationResult(verdict="non_answer",score=1,confidence=.99,strategy_summary="Aucune stratégie mathématique exploitable.",reference_relationship="no_meaningful_strategy",rubric=EvaluationRubric(mathematical_correctness=0,rigor=0,clarity=1,efficiency=0),strengths=[],issues=[MathIssue(severity="major",category="other",description="La copie ne répond pas au problème.",candidate_excerpt=None)],missing_justifications=[],key_feedback="Rédigez une démonstration.",reference_method_summary="Le corrigé établit le résultat demandé.",suggested_improvement="Commencez par identifier les hypothèses et la conclusion.")
        return EvaluationResult(verdict="mostly_correct",score=16,confidence=.91,strategy_summary="La copie développe un raisonnement direct.",reference_relationship="alternative_valid_strategy",rubric=EvaluationRubric(mathematical_correctness=8,rigor=3.5,clarity=1.5,efficiency=3),strengths=["Idée principale trouvée","Calculs cohérents"],issues=[MathIssue(severity="minor",category="rigor",description="Une transition mérite une justification explicite.",candidate_excerpt=None)],missing_justifications=["Justifier la transition centrale."],key_feedback="Le raisonnement est globalement juste.",reference_method_summary="Le corrigé utilise une méthode différente.",suggested_improvement="Explicitez la transition centrale.")


class HuggingFaceProvider:
    name = "huggingface"
    def __init__(self, *, client=None, family: ModelFamily | str | None = None):
        if not settings.hf_token and client is None:
            raise RuntimeError("HF_TOKEN is not configured")
        self.family = ModelFamily(family or settings.llm_model_family)
        self.model = resolve_model(self.family, ModelRole.DEEP)
        self._client = client or AsyncOpenAI(base_url=settings.hf_router_base_url, api_key=settings.hf_token, timeout=settings.hf_timeout_seconds)
        self.last_request: dict | None = None

    async def structured_response(self, *, instructions, input_text, response_model, role=ModelRole.DEEP, family=None):
        role, family = ModelRole(role), ModelFamily(family or self.family)
        model = resolve_model(family, role); _, backend = model_identity(model)
        schema = response_model.model_json_schema()
        started = time.perf_counter()
        log = component_logger("inference").bind(family=family.value, role=role.value, model=model, backend=backend)
        log.info("request_started")
        for attempt in range(3):
            try:
                response = await self._client.chat.completions.create(
                    model=model, messages=[{"role":"system","content":instructions},{"role":"user","content":input_text}],
                    temperature=.2 if role is ModelRole.FAST else .1,
                    max_tokens=settings.hf_fast_max_tokens if role is ModelRole.FAST else settings.hf_deep_max_tokens,
                    response_format={"type":"json_schema","json_schema":{"name":response_model.__name__,"strict":True,"schema":schema}},
                )
                content = response.choices[0].message.content if response.choices else None
                if not content: raise RemoteLLMError("remote_empty_response", "Remote provider returned no content")
                try: result = response_model.model_validate(json.loads(content))
                except json.JSONDecodeError as exc: raise RemoteLLMError("remote_invalid_json", "Remote provider returned invalid JSON") from exc
                except ValidationError as exc: raise RemoteLLMError("remote_schema_error", "Remote response failed schema validation") from exc
                usage = response.usage
                latency = round((time.perf_counter()-started)*1000, 1)
                self.last_request = {"model":model,"provider":backend,"family":family.value,"role":role.value,"latency_ms":latency,
                    "prompt_tokens":getattr(usage,"prompt_tokens",None),"completion_tokens":getattr(usage,"completion_tokens",None),"total_tokens":getattr(usage,"total_tokens",None)}
                log.info("request complete latency_ms={} prompt_tokens={} completion_tokens={} total_tokens={} http_status=200", latency, self.last_request["prompt_tokens"], self.last_request["completion_tokens"], self.last_request["total_tokens"])
                return result
            except RemoteLLMError: raise
            except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                retryable = isinstance(exc, APIConnectionError) or status in {429,502,503,504}
                if retryable and attempt < 2:
                    await __import__("asyncio").sleep(.15 * 2**attempt + random.random()*.1); continue
                if isinstance(exc, APITimeoutError): code="remote_timeout"
                elif isinstance(exc, RateLimitError) or status == 429: code="remote_rate_limit"
                elif isinstance(exc, APIConnectionError): code="remote_connection_error"
                elif status == 401: code="remote_auth_error"
                elif status == 403 and family is ModelFamily.GEMMA: code="GEMMA_LICENSE_NOT_ACCEPTED"
                elif status == 403: code="HF_PERMISSION_OR_MODEL_ACCESS_DENIED"
                elif status == 400: code="remote_llm_schema_unsupported"
                else: code="remote_provider_error"
                log.warning("request failed error_code={} http_status={}", code, status)
                raise RemoteLLMError(code, code, status=status) from exc
        raise AssertionError("unreachable")


class OpenAIProvider:
    name="openai"
    def __init__(self): self.model=settings.llm_model
    async def structured_response(self, *, instructions, input_text, response_model, **_):
        if not settings.openai_api_key: raise RuntimeError("OPENAI_API_KEY is not configured")
        response=await AsyncOpenAI(api_key=settings.openai_api_key,timeout=settings.llm_timeout_seconds).responses.parse(model=self.model,instructions=instructions,input=input_text,text_format=response_model)
        if response.output_parsed is None: raise ValueError("provider returned no structured output")
        return response.output_parsed


def provider_from_settings():
    if settings.llm_provider=="fake": return FakeLLMProvider()
    if settings.llm_provider=="openai": return OpenAIProvider()
    if settings.llm_provider=="huggingface": return HuggingFaceProvider()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
