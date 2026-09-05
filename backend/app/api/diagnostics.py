import hmac
import re
from collections import deque
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.services.inference_diagnostics import diagnose
from app.providers.llm import HuggingFaceProvider, ModelRole, RemoteLLMError, model_identity
from app.schemas.evaluation import InferenceDiagnosticsResponse

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

# Redaction is deliberately applied again at the API boundary.  This protects
# operators from accidental secret output produced by dependencies (not only
# messages emitted by KholleLab itself).
_REDACTIONS = (
    (re.compile(r"(?i)\b(HF_TOKEN|OPENAI_API_KEY|X-Diagnostics-Token)\b\s*[:=]\s*([^\s,;]+)"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[^\s,;]+"), "Authorization: [REDACTED]"),
    (re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s/@]+:)([^@\s]+)(@)"), r"\1[REDACTED]\3"),
)


def redact_log_line(line: str) -> str:
    for pattern, replacement in _REDACTIONS:
        line = pattern.sub(replacement, line)
    return line


class LogSource(str, Enum):
    application = "application"
    inference = "inference"


def authorize(x_diagnostics_token: str | None = Header(default=None)) -> None:
    if not settings.diagnostics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    expected = settings.diagnostics_token or ""
    if not expected or not x_diagnostics_token or not hmac.compare_digest(expected, x_diagnostics_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid diagnostics token")


@router.get("/inference", response_model=InferenceDiagnosticsResponse, dependencies=[])
async def inference_diagnostic(x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    return await diagnose()


@router.get("/logs")
def logs(source: LogSource, lines: int = Query(200, ge=1, le=500), x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    filenames = {LogSource.application: "khollelab.log", LogSource.inference: "inference.log"}
    path = Path(settings.runtime_logs_dir) / filenames[source]
    if not path.is_file():
        return {"source": source, "lines": [], "available": False}
    with path.open(encoding="utf-8", errors="replace") as stream:
        tail = list(deque(stream, maxlen=lines))
    return {"source": source, "lines": [redact_log_line(line.rstrip("\n")) for line in tail], "available": True}


class DiagnosticAnswer(BaseModel):
    answer: str

@router.post("/inference/test")
async def test_completion(role: ModelRole = Query(ModelRole.FAST), x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    if settings.llm_provider != "huggingface": raise HTTPException(status_code=409, detail="Hugging Face provider is not configured")
    prompt = "Pose une seule question courte pour aider un élève à résoudre 3x-7=11, sans donner la réponse." if role is ModelRole.FAST else "Réponds uniquement avec la valeur de x dans 3x-7=11."
    try:
        provider=HuggingFaceProvider(); result=await provider.structured_response(instructions="Réponds au format JSON demandé.",input_text=prompt,response_model=DiagnosticAnswer,role=role)
    except RemoteLLMError as exc: return {"status":"fail","error_code":exc.code}
    info=provider.last_request or {}; name, backend=model_identity(info.get("model",provider.model))
    return {"status":"pass","model":name,"provider":backend,"latency_ms":info.get("latency_ms"),"tokens":info.get("total_tokens"),"estimated_cost_usd":None,"response_preview":result.answer[:80]}
