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

REMOTE_CODES = {
    "auth": "REMOTE_AUTH", "access": "REMOTE_ACCESS_DENIED",
    "rate": "REMOTE_RATE_LIMITED", "timeout": "REMOTE_TIMEOUT",
    "connection": "REMOTE_CONNECTION", "provider": "REMOTE_PROVIDER",
    "truncated": "REMOTE_TRUNCATED", "json": "REMOTE_INVALID_JSON",
    "schema": "REMOTE_SCHEMA",
}


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
        self.family = ModelFamily(family or settings.llm_model_family)
        self.model = resolve_model(self.family, ModelRole.DEEP)
        self._client = client
        self.last_request: dict | None = None

    async def structured_response(self, *, instructions, input_text, response_model, role=ModelRole.DEEP, family=None):
        if self._client is None:
            if not settings.hf_token:
                raise RemoteLLMError(REMOTE_CODES["auth"], "HF_TOKEN is not configured")
            self._client = AsyncOpenAI(base_url=settings.hf_router_base_url, api_key=settings.hf_token, timeout=settings.hf_timeout_seconds)
        role, family = ModelRole(role), ModelFamily(family or self.family)
        model = resolve_model(family, role); _, backend = model_identity(model)
        schema = response_model.model_json_schema()
        started = time.perf_counter()
        if role is ModelRole.FAST:
            initial_max_tokens, retry_max_tokens = settings.hf_fast_max_tokens, settings.hf_fast_retry_max_tokens
        elif response_model is CandidateAudit:
            initial_max_tokens, retry_max_tokens = settings.hf_examiner_audit_max_tokens, 1536
        else:
            initial_max_tokens, retry_max_tokens = settings.hf_examiner_adjudication_max_tokens, 2048
        log = component_logger("inference").bind(family=family.value, role=role.value, model=model, backend=backend)
        log.info("request_started initial_max_tokens={} retry_max_tokens={} max_tokens={}", initial_max_tokens, retry_max_tokens, initial_max_tokens)
        transient_attempt = 0
        truncation_retry = 0
        max_tokens = initial_max_tokens
        while True:
            try:
                response = await self._client.chat.completions.create(
                    model=model, messages=[{"role":"system","content":instructions},{"role":"user","content":input_text}],
                    temperature=.2 if role is ModelRole.FAST else .1,
                    max_tokens=max_tokens,
                    response_format={"type":"json_schema","json_schema":{"name":response_model.__name__,"strict":True,"schema":schema}},
                )
                choice = response.choices[0] if response.choices else None
                content = choice.message.content if choice else None
                finish_reason = getattr(choice, "finish_reason", None)
                usage = response.usage
                completion_tokens = getattr(usage, "completion_tokens", None)
                if finish_reason in {"length", "max_tokens"}:
                    log.warning("request_truncated finish_reason={} completion_tokens={} max_tokens={} retry_count={} schema_requested=true schema_validated=false", finish_reason, completion_tokens, max_tokens, truncation_retry)
                    if truncation_retry == 0 and retry_max_tokens > max_tokens:
                        log.info("structured_retry reason=truncated old_max_tokens={} new_max_tokens={}", max_tokens, retry_max_tokens)
                        truncation_retry, max_tokens = 1, retry_max_tokens
                        continue
                    raise RemoteLLMError(REMOTE_CODES["truncated"], "Remote response exceeded its output budget")
                if not content: raise RemoteLLMError(REMOTE_CODES["provider"], "Remote provider returned no content")
                try: result = response_model.model_validate(json.loads(content))
                except json.JSONDecodeError as exc:
                    last_type = "whitespace" if content[-1:].isspace() else "punctuation" if not content[-1:].isalnum() else "alphanumeric"
                    log.warning("malformed_response response_character_count={} completion_tokens={} finish_reason={} last_nonsecret_character_type={} schema_requested=true schema_validated=false", len(content), completion_tokens, finish_reason, last_type)
                    raise RemoteLLMError(REMOTE_CODES["json"], "Remote provider returned invalid JSON") from exc
                except ValidationError as exc:
                    log.warning("schema_validation_failed response_character_count={} completion_tokens={} finish_reason={} schema_requested=true schema_validated=false", len(content), completion_tokens, finish_reason)
                    raise RemoteLLMError(REMOTE_CODES["schema"], "Remote response failed schema validation") from exc
                latency = round((time.perf_counter()-started)*1000, 1)
                self.last_request = {"model":model,"provider":backend,"family":family.value,"role":role.value,"latency_ms":latency,
                    "prompt_tokens":getattr(usage,"prompt_tokens",None),"completion_tokens":completion_tokens,"total_tokens":getattr(usage,"total_tokens",None),
                    "finish_reason":finish_reason,"max_tokens":max_tokens,"schema_requested":True,"schema_validated":True,"retry_count":truncation_retry}
                log.info("request_complete latency_ms={} prompt_tokens={} completion_tokens={} total_tokens={} max_tokens={} finish_reason={} schema_requested=true schema_validated=true retry_count={} http_status=200", latency, self.last_request["prompt_tokens"], completion_tokens, self.last_request["total_tokens"], max_tokens, finish_reason, truncation_retry)
                return result
            except RemoteLLMError: raise
            except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                retryable = isinstance(exc, APIConnectionError) or status in {429,502,503,504}
                if retryable and transient_attempt < 2:
                    await __import__("asyncio").sleep(.15 * 2**transient_attempt + random.random()*.1); transient_attempt += 1; continue
                if isinstance(exc, APITimeoutError): code=REMOTE_CODES["timeout"]
                elif isinstance(exc, RateLimitError) or status == 429: code=REMOTE_CODES["rate"]
                elif isinstance(exc, APIConnectionError): code=REMOTE_CODES["connection"]
                elif status == 401: code=REMOTE_CODES["auth"]
                elif status == 403: code=REMOTE_CODES["access"]
                elif status == 400: code=REMOTE_CODES["schema"]
                else: code=REMOTE_CODES["provider"]
                log.warning("request failed error_code={} http_status={}", code, status)
                raise RemoteLLMError(code, code, status=status) from exc


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
