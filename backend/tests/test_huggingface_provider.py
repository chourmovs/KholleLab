from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from app.core.config import settings
from app.providers.llm import HuggingFaceProvider, ModelRole, RemoteLLMError, resolve_model
class Answer(BaseModel): answer: int
class Completions:
    def __init__(self, responses='{"answer": 6}'):
        self.responses=list(responses) if isinstance(responses,list) else [responses]; self.calls=[]
    async def create(self, **kwargs):
        self.calls.append(kwargs); item=self.responses.pop(0)
        content,finish=item if isinstance(item,tuple) else (item,"stop")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content),finish_reason=finish)],usage=SimpleNamespace(prompt_tokens=8,completion_tokens=kwargs["max_tokens"] if finish=="length" else 4,total_tokens=12))
class Client:
    def __init__(self, responses='{"answer": 6}'):
        self.completions=Completions(responses); self.chat=SimpleNamespace(completions=self.completions)
@pytest.mark.parametrize(('family','role','expected'),[('qwen','fast','Qwen/Qwen3-8B:nscale'),('qwen','deep','Qwen/Qwen3-32B:nscale'),('gemma','fast','google/gemma-3-12b-it:deepinfra'),('gemma','deep','google/gemma-3-27b-it:deepinfra')])
def test_resolver(family,role,expected): assert resolve_model(family,role)==expected
@pytest.mark.asyncio
async def test_strict_structured_completion_records_finish_reason():
    client=Client(); provider=HuggingFaceProvider(client=client)
    result=await provider.structured_response(instructions='safe',input_text='equation',response_model=Answer,role=ModelRole.FAST)
    assert result.answer==6
    assert client.completions.calls[0]['response_format']['json_schema']['strict'] is True
    assert provider.last_request['total_tokens']==12
    assert provider.last_request['finish_reason']=='stop'
    assert provider.last_request['schema_validated'] is True
@pytest.mark.asyncio
@pytest.mark.parametrize(('content','code'),[('not json','REMOTE_INVALID_JSON'),('{"answer":"wrong"}','REMOTE_SCHEMA'),('', 'REMOTE_PROVIDER')])
async def test_remote_response_validation(content,code):
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=Client(content)).structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code==code
@pytest.mark.asyncio
async def test_truncation_retries_once_and_succeeds(monkeypatch):
    monkeypatch.setattr(settings,'hf_examiner_adjudication_max_tokens',1536)
    client=Client([('{"answer":', 'length'),('{"answer": 6}','stop')]); provider=HuggingFaceProvider(client=client)
    assert (await provider.structured_response(instructions='',input_text='',response_model=Answer)).answer==6
    assert [call['max_tokens'] for call in client.completions.calls]==[1536,2048]
    assert provider.last_request['retry_count']==1
@pytest.mark.asyncio
async def test_second_truncation_is_controlled():
    client=Client([('partial','length'),('partial again','length')])
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=client).structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code=='REMOTE_TRUNCATED'
    assert len(client.completions.calls)==2

def test_token_required(monkeypatch):
    monkeypatch.setattr(settings,'hf_token',None)
    assert HuggingFaceProvider().model

@pytest.mark.asyncio
async def test_missing_token_is_normalized(monkeypatch):
    monkeypatch.setattr(settings,'hf_token',None)
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider().structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code == "REMOTE_AUTH"
