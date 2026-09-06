from types import SimpleNamespace
import httpx
import pytest
from pydantic import BaseModel
from app.core.config import settings
from app.providers.llm import HuggingFaceProvider, ModelRole, RemoteLLMError, resolve_model
from openai import APIConnectionError, APIStatusError, APITimeoutError
from app.schemas.evaluation import CandidateAudit
class Answer(BaseModel): answer: int
class Completions:
    def __init__(self, responses='{"answer": 6}'):
        self.responses=list(responses) if isinstance(responses,list) else [responses]; self.calls=[]
    async def create(self, **kwargs):
        self.calls.append(kwargs); item=self.responses.pop(0)
        if isinstance(item,Exception): raise item
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
    assert provider.last_request['retry_count']==0
    assert len(client.completions.calls)==1
    assert client.completions.calls[0]['max_tokens']==512
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
async def test_fast_truncation_uses_dedicated_retry_budget(monkeypatch):
    monkeypatch.setattr(settings,'hf_fast_max_tokens',512); monkeypatch.setattr(settings,'hf_fast_retry_max_tokens',768)
    client=Client([('{"answer":', 'length'),('{"answer": 6}','stop')]); provider=HuggingFaceProvider(client=client)
    assert (await provider.structured_response(instructions='',input_text='',response_model=Answer,role=ModelRole.FAST)).answer==6
    assert [call['max_tokens'] for call in client.completions.calls]==[512,768]
    assert provider.last_request['retry_count']==1
@pytest.mark.asyncio
async def test_fast_double_truncation_stops_after_retry(monkeypatch):
    monkeypatch.setattr(settings,'hf_fast_max_tokens',512); monkeypatch.setattr(settings,'hf_fast_retry_max_tokens',768)
    client=Client([('partial','length'),('partial again','length')])
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=client).structured_response(instructions='',input_text='',response_model=Answer,role=ModelRole.FAST)
    assert caught.value.code=='REMOTE_TRUNCATED'
    assert [call['max_tokens'] for call in client.completions.calls]==[512,768]
@pytest.mark.asyncio
async def test_second_truncation_is_controlled():
    client=Client([('partial','length'),('partial again','length')])
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=client).structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code=='REMOTE_TRUNCATED'
    assert len(client.completions.calls)==2

@pytest.mark.parametrize(('response_model','expected'),[(CandidateAudit,1024),(Answer,1536)])
@pytest.mark.asyncio
async def test_deep_initial_budgets_are_unchanged(response_model,expected):
    audit='{"strategy_summary":"Résumé.","claims":[],"major_errors":[],"minor_errors":[],"missing_justifications":[],"conclusion_reached":true,"conclusion_supported":true,"provisional_status":"correct"}'
    client=Client(audit if response_model is CandidateAudit else '{"answer": 6}')
    await HuggingFaceProvider(client=client).structured_response(instructions='',input_text='',response_model=response_model,role=ModelRole.DEEP)
    assert client.completions.calls[0]['max_tokens']==expected

def test_token_required(monkeypatch):
    monkeypatch.setattr(settings,'hf_token',None)
    assert HuggingFaceProvider().model

@pytest.mark.asyncio
async def test_missing_token_is_normalized(monkeypatch):
    monkeypatch.setattr(settings,'hf_token',None)
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider().structured_response(instructions='',input_text='',response_model=Answer)
    assert caught.value.code == "REMOTE_AUTH"
    assert caught.value.retryable is False

def status_error(status, retry_after=None):
    request=httpx.Request("POST","https://router.invalid/v1/chat/completions")
    response=httpx.Response(status,request=request,headers={"retry-after":retry_after} if retry_after else {})
    return APIStatusError("provider failure",response=response,body={"error":"not logged"})

@pytest.mark.asyncio
@pytest.mark.parametrize("failure",[status_error(503),status_error(429,"0"),APITimeoutError(httpx.Request("POST","https://router.invalid")),APIConnectionError(request=httpx.Request("POST","https://router.invalid"))])
async def test_transient_transport_failure_retries_then_succeeds(monkeypatch,failure):
    monkeypatch.setattr(settings,"hf_retry_base_seconds",0)
    monkeypatch.setattr(settings,"hf_retry_jitter_seconds",0)
    client=Client([failure,'{"answer": 6}'])
    assert (await HuggingFaceProvider(client=client).structured_response(instructions="",input_text="",response_model=Answer)).answer==6
    assert len(client.completions.calls)==2

@pytest.mark.asyncio
async def test_repeated_503_is_bounded_and_retryable(monkeypatch):
    monkeypatch.setattr(settings,"hf_request_max_attempts",3)
    monkeypatch.setattr(settings,"hf_retry_base_seconds",0)
    monkeypatch.setattr(settings,"hf_retry_jitter_seconds",0)
    client=Client([status_error(503),status_error(503),status_error(503)])
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=client).structured_response(instructions="",input_text="",response_model=Answer)
    assert caught.value.retryable is True and caught.value.status==503
    assert len(client.completions.calls)==3

@pytest.mark.asyncio
@pytest.mark.parametrize("status",[400,401,403])
async def test_permanent_http_failures_are_not_retried(status):
    client=Client([status_error(status)])
    with pytest.raises(RemoteLLMError) as caught:
        await HuggingFaceProvider(client=client).structured_response(instructions="",input_text="",response_model=Answer)
    assert caught.value.retryable is False
    assert len(client.completions.calls)==1
