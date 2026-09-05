import asyncio
import socket
import time
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core.logging import component_logger

log = component_logger("inference")


def public_model_name() -> str:
    return settings.local_llm_model.rsplit("/", 1)[-1].removesuffix("-GGUF")


def _target() -> tuple[str, int, str]:
    parsed = urlparse(settings.local_llm_base_url)
    if not parsed.hostname:
        raise ValueError("invalid inference URL")
    return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), settings.local_llm_base_url.removesuffix("/v1").rstrip("/")


async def diagnose() -> dict:
    result = {"provider": settings.llm_provider, "backend": "llama.cpp" if settings.llm_provider == "local" else settings.llm_provider, "model": public_model_name(), "quantization": settings.local_llm_quant,
              "status": "unavailable", "reason": "connection_failed",
              "checks": {"provider_config": "fail", "dns": "not_run", "tcp_8080": "not_run", "health": "not_run", "models": "not_run"}}
    if settings.llm_provider != "local":
        result.update(status="disabled", reason="provider_disabled")
        return result
    result["checks"]["provider_config"] = "pass"
    try:
        host, port, root = _target()
        log.debug("Health probe started provider=local model={} quant={}", public_model_name(), settings.local_llm_quant)
        await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, host, port)
        result["checks"]["dns"] = "pass"
    except socket.gaierror:
        log.exception("DNS resolution failed error_code=dns_error")
        result["reason"] = "dns_error"
        result["checks"]["dns"] = "fail"
        return result
    except ValueError:
        result.update(status="error", reason="invalid_configuration")
        return result
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3)
        writer.close()
        await writer.wait_closed()
        result["checks"]["tcp_8080"] = "pass"
    except (OSError, asyncio.TimeoutError):
        log.exception("TCP connection failed error_code=connection_refused")
        result["reason"] = "connection_refused"
        result["checks"]["tcp_8080"] = "fail"
        return result
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=min(5, settings.local_llm_timeout_seconds)) as client:
            health = await client.get(f"{root}/health")
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            log.debug("Health probe complete status={} elapsed_ms={}", health.status_code, elapsed)
            if health.status_code != 200:
                result["checks"]["health"] = "fail"
                result.update(status="starting" if health.status_code == 503 else "error", reason="model_loading" if health.status_code == 503 else "unexpected_http_status", latency_ms=elapsed)
                return result
            result["checks"]["health"] = "pass"
            models = await client.get(f"{root}/v1/models")
            if models.status_code == 200:
                result["checks"]["models"] = "pass"
                result.update(status="ready", reason=None, latency_ms=elapsed)
            else:
                result["checks"]["models"] = "fail"
                result.update(status="error", reason="models_endpoint_failed", latency_ms=elapsed)
    except httpx.TimeoutException:
        log.exception("Inference probe timed out error_code=timeout")
        result["reason"] = "timeout"
        result["checks"]["health"] = "fail"
    except httpx.RequestError:
        log.exception("Inference HTTP probe failed error_code=connection_failed")
        result["checks"]["health"] = "fail"
    return result
