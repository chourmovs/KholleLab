import time

import httpx

from app.core.config import settings
from app.providers.llm import ModelRole, model_identity, resolve_model

_cache: tuple[float, dict] | None = None


def configured_identity() -> dict:
    fast, deep = resolve_model(settings.llm_model_family, ModelRole.FAST), resolve_model(settings.llm_model_family, ModelRole.DEEP)
    fast_name, fast_backend = model_identity(fast); deep_name, deep_backend = model_identity(deep)
    return {"provider": settings.llm_provider, "family": settings.llm_model_family.value,
            "fast_model": fast_name, "fast_backend": fast_backend,
            "deep_model": deep_name, "deep_backend": deep_backend}


def cached_status() -> str:
    """Return capability state without performing any network I/O.

    Application health checks must remain independent of the remote provider.
    The richer status endpoint is responsible for refreshing this cache.
    """
    if settings.llm_provider != "huggingface":
        return "disabled"
    if not settings.hf_token:
        return "error"
    return _cache[1].get("status", "unavailable") if _cache else "unavailable"


async def diagnose(*, force=False) -> dict:
    global _cache
    identity = configured_identity()
    if settings.llm_provider != "huggingface":
        return {**identity, "status":"disabled", "reason":"provider_disabled", "checks":{"provider_config":"pass","router":"not_run","authentication":"not_run","structured_output":"not_run"}}
    if not settings.hf_token:
        return {**identity, "status":"error", "reason":"HF_TOKEN_MISSING", "checks":{"provider_config":"fail","router":"not_run","authentication":"fail","structured_output":"not_run"}}
    now = time.monotonic()
    if not force and _cache:
        ttl = 60 if _cache[1].get("status") == "ready" else 15
        if now-_cache[0] < ttl: return _cache[1]
    result = {**identity,"status":"unavailable","reason":"connection_failed","checks":{"provider_config":"pass","router":"fail","authentication":"not_run","structured_output":"not_tested"}}
    started=time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=min(settings.hf_timeout_seconds, 5)) as client:
            response=await client.get(f"{settings.hf_router_base_url.rstrip('/')}/models",headers={"Authorization":f"Bearer {settings.hf_token}"})
        result["latency_ms"]=round((time.perf_counter()-started)*1000,1); result["checks"]["router"]="pass"
        if response.status_code == 401: result.update(status="error",reason="HF_TOKEN_INVALID"); result["checks"]["authentication"]="fail"
        elif response.status_code == 403: result.update(status="error",reason="HF_PERMISSION_OR_MODEL_ACCESS_DENIED"); result["checks"]["authentication"]="fail"
        elif response.is_success: result.update(status="ready",reason=None); result["checks"]["authentication"]="pass"
        else: result.update(status="error",reason="remote_provider_error")
    except httpx.RequestError: pass
    _cache=(now,result)
    return result
