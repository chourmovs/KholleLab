import httpx
import pytest
from pydantic import BaseModel
from app.core.config import settings
from app.providers.llm import InferenceProfile, LocalLLMError, LocalLLMProvider, provider_from_settings
class Answer(BaseModel): value: int
def client(handler): return httpx.AsyncClient(transport=httpx.MockTransport(handler))
@pytest.mark.asyncio
@pytest.mark.parametrize("profile,expected", [(InferenceProfile.FAST, (.2,.9,192)),(InferenceProfile.DEEP,(.1,.95,768))])
async def test_success_and_profile_settings(profile,expected):
    seen={}
    def handler(request):
        seen.update(__import__('json').loads(request.content)); return httpx.Response(200,json={"choices":[{"message":{"content":'{"value":56}'}}]})
    async with client(handler) as http: result=await LocalLLMProvider(client=http).structured_response(instructions="math",input_text="7x8",response_model=Answer,profile=profile)
    assert result.value==56
    assert (seen['temperature'],seen['top_p'],seen['max_tokens'])==expected
@pytest.mark.asyncio
@pytest.mark.parametrize("handler,message",[
 (lambda r: (_ for _ in ()).throw(httpx.ReadTimeout('slow')),"unavailable"),
 (lambda r: (_ for _ in ()).throw(httpx.ConnectError('refused')),"unavailable"),
 (lambda r:httpx.Response(500),"HTTP 500"),
 (lambda r:httpx.Response(200,json={"choices":[]}),"no choices"),
 (lambda r:httpx.Response(200,json={"choices":[{"message":{"content":"not-json"}}]}),"malformed")])
async def test_controlled_failures(handler,message):
    async with client(handler) as http:
        with pytest.raises(LocalLLMError,match=message): await LocalLLMProvider(client=http).structured_response(instructions="",input_text="",response_model=Answer)
def test_configuration_errors(monkeypatch):
    monkeypatch.setattr(settings,'local_llm_base_url','not-a-url')
    with pytest.raises(RuntimeError,match='HTTP'): LocalLLMProvider()
def test_factory_keeps_all_providers(monkeypatch):
    for configured,name in [('fake','fake'),('openai','openai'),('local','local')]:
        monkeypatch.setattr(settings,'llm_provider',configured); assert provider_from_settings().name==name
    monkeypatch.setattr(settings,'llm_provider','mystery')
    with pytest.raises(RuntimeError,match='Unsupported'): provider_from_settings()
