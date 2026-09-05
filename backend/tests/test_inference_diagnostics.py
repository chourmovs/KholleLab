from types import SimpleNamespace
import httpx
import pytest
from app.core.config import settings
from app.services import inference_diagnostics as diagnostic

class Client:
    def __init__(self,response=None,error=None,**_): self.response=response;self.error=error
    async def __aenter__(self): return self
    async def __aexit__(self,*_): pass
    async def get(self,*_,**__):
        if self.error: raise self.error
        return self.response

@pytest.mark.asyncio
async def test_disabled_and_missing_token(monkeypatch):
    monkeypatch.setattr(settings,"llm_provider","fake")
    assert (await diagnostic.diagnose(force=True))["status"]=="disabled"
    monkeypatch.setattr(settings,"llm_provider","huggingface");monkeypatch.setattr(settings,"hf_token",None)
    result=await diagnostic.diagnose(force=True);assert result["status"]=="error" and result["reason"]=="HF_TOKEN_MISSING"

@pytest.mark.asyncio
@pytest.mark.parametrize(("status","reason"),[(401,"HF_TOKEN_INVALID"),(403,"HF_PERMISSION_OR_MODEL_ACCESS_DENIED")])
async def test_auth_statuses(monkeypatch,status,reason):
    monkeypatch.setattr(settings,"llm_provider","huggingface");monkeypatch.setattr(settings,"hf_token","secret")
    response=SimpleNamespace(status_code=status,is_success=False)
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kwargs:Client(response=response))
    result=await diagnostic.diagnose(force=True);assert result["reason"]==reason

@pytest.mark.asyncio
async def test_connection_failure(monkeypatch):
    monkeypatch.setattr(settings,"llm_provider","huggingface");monkeypatch.setattr(settings,"hf_token","secret")
    request=httpx.Request("GET","https://example.test")
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kwargs:Client(error=httpx.ConnectError("down",request=request)))
    result=await diagnostic.diagnose(force=True);assert result["status"]=="unavailable" and result["reason"]=="connection_failed"
