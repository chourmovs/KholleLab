from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from app.core.config import ModelFamily, settings
from app.providers.llm import HuggingFaceProvider, ModelRole, RemoteLLMError, resolve_model
class Answer(BaseModel): answer: int
class Completions:
    def __init__(self, content='{"answer": 6}'): self.content=content; self.calls=[]
    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],usage=SimpleNamespace(prompt_tokens=8,completion_tokens=4,total_tokens=12))
class Client:
    def __init__(self, content='{"answer": 6}'):
        self.completions=Completions(content); self.chat=SimpleNamespace(completions=self.completions)
@pytest.mark.parametrize(('family','role','expected'),[
 ('qwen','fast','Qwen/Qwen3-8B:nscale'),('qwen','deep','Qwen/Qwen3-32B:nscale'),
 ('gemma','fast','google/gemma-3-12b-it:deepinfra'),('gemma','deep','google/gemma-3-27b-it:deepinfra')])
def test_resolver(family,role,expected): assert resolve_model(family,role)==expected
@pytest.mark.asyncio
async def test_strict_structured_completion():
    client=Client(); provider=HuggingFaceProvider(client=client)
    result=await provider.structured_response(instructions='safe',input_text='equation',response_model=Answer,role=ModelRole.FAST)
    assert result.answer==6
    assert client.completions.calls[0]['response_format']['json_schema']['strict'] is True
    assert provider.last_request['total_tokens']==12
@pytest.mark.asyncio
@pytest.mark.parametrize(('content','code'),[('not json','remote_invalid_json'),('{"answer":"wrong"}','remote_schema_error'),('', 'remote_empty_response')])
async def test_remote_response_validation(content,code):
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=Client(content)).structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code==code

def test_token_required(monkeypatch):
    monkeypatch.setattr(settings,'hf_token',None)
    with pytest.raises(RuntimeError,match='HF_TOKEN'): HuggingFaceProvider()
