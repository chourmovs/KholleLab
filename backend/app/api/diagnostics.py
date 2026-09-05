import hmac
import re
import time
from collections import deque
from enum import Enum
from pathlib import Path

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.core.config import settings
from app.services.inference_diagnostics import diagnose, public_model_name

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


@router.get("/inference", dependencies=[])
async def inference_diagnostic(x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    return await diagnose()


@router.get("/logs")
def logs(source: LogSource, lines: int = Query(200, ge=1, le=500), x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    filenames = {LogSource.application: "khollelab.log", LogSource.inference: "llama.log"}
    path = Path(settings.runtime_logs_dir) / filenames[source]
    if not path.is_file():
        return {"source": source, "lines": [], "available": False}
    with path.open(encoding="utf-8", errors="replace") as stream:
        tail = list(deque(stream, maxlen=lines))
    return {"source": source, "lines": [redact_log_line(line.rstrip("\n")) for line in tail], "available": True}


@router.post("/inference/test")
async def test_completion(x_diagnostics_token: str | None = Header(default=None)):
    authorize(x_diagnostics_token)
    if settings.llm_provider != "local":
        raise HTTPException(status_code=409, detail="Local provider is not configured")
    started = time.perf_counter()
    payload = {"model": settings.local_llm_model, "messages": [{"role": "user", "content": "Réponds uniquement par 56 : combien font 7 × 8 ?"}], "temperature": 0, "max_tokens": 16}
    try:
        async with httpx.AsyncClient(timeout=settings.local_llm_timeout_seconds) as client:
            response = await client.post(f"{settings.local_llm_base_url.rstrip('/')}/chat/completions", json=payload)
            response.raise_for_status()
            preview = response.json()["choices"][0]["message"]["content"].strip()[:80]
    except httpx.TimeoutException:
        return {"status": "fail", "reason": "timeout", "error_code": "LOCAL_LLM_TIMEOUT"}
    except httpx.ConnectError:
        return {"status": "fail", "reason": "connection_refused", "error_code": "LOCAL_LLM_UNAVAILABLE"}
    except httpx.HTTPStatusError:
        return {"status": "fail", "reason": "http_error", "error_code": "LOCAL_LLM_HTTP_ERROR"}
    except (httpx.RequestError, KeyError, ValueError, TypeError):
        return {"status": "fail", "reason": "invalid_response", "error_code": "LOCAL_LLM_INVALID_JSON"}
    return {"status": "pass" if "56" in preview else "fail", "latency_ms": round((time.perf_counter()-started)*1000, 1), "response_preview": preview, "model": public_model_name()}
