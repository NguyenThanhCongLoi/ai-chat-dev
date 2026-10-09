"""Gateway transport, retry, fallback and structured LLM responses."""
import concurrent.futures
import json
import os
import re
import threading
import time
import httpx
from .timeouts import gateway_connect_timeout

_UNSET_MODEL=object()
_gateway_pool=concurrent.futures.ThreadPoolExecutor(max_workers=32,thread_name_prefix="gateway")
_gateway_slots=threading.BoundedSemaphore(32)


def _within_deadline(call, timeout):
    """Bound caller latency, including pool wait; never queue unlimited work."""
    deadline=time.monotonic()+timeout
    if not _gateway_slots.acquire(timeout=timeout):
        raise httpx.PoolTimeout("Gateway capacity deadline exceeded")
    try:
        future=_gateway_pool.submit(call)
    except BaseException:
        _gateway_slots.release()
        raise
    future.add_done_callback(lambda _: _gateway_slots.release())
    try:
        return future.result(timeout=max(0,deadline-time.monotonic()))
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise httpx.ReadTimeout("Gateway total deadline exceeded") from None

class TokenLimitError(RuntimeError):
    """The gateway returned a truncated completion."""

class LLM:
    def __init__(self):
        self.url=os.getenv("LLM_API_BASE","https://gateway.avibi.ai/v1").rstrip("/")
        self.model=os.getenv("LLM_MODEL","openai/gpt-4.1-mini")
        self.fallback_model=os.getenv("LLM_FALLBACK_MODEL","")
        self.fallback_model_2=""
        self.default_temperature=.75
        self.short_temperature=.65
        self.default_max_tokens=350
        self.short_max_tokens=180
        self.api_key=(os.getenv("AIMP_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        self.model_api_keys={}
        self.model_api_bases={}
        self.model_wire_ids={}
        self.model_thinking_modes={}
        self.model_reasoning_efforts={}
        self.model_generation={}
        self.model_gateway_timeouts={}
        self.purpose_models={}
        self.fallback_instruction=""
        self._clients={}
    def _request(self,messages,temperature,max_tokens,model,timeout_seconds=None):
        api_key=self.model_api_keys.get(model,self.api_key)
        api_base=self.model_api_bases.get(model,self.url)
        wire_model=self.model_wire_ids.get(model,model)
        if not api_key:raise RuntimeError(f"Chưa cấu hình API key cho {api_base}")
        headers={"Content-Type":"application/json","Authorization":"Bearer "+api_key}
        payload={"model":wire_model,"messages":messages}
        if "gpt-5" in wire_model:
            payload["max_completion_tokens"]=max_tokens
        else:
            payload.update({"temperature":temperature,"max_tokens":max_tokens})
        thinking=self.model_thinking_modes.get(model,"default")
        effort=self.model_reasoning_efforts.get(model,"default")
        if thinking in ("enabled","disabled"):payload["thinking"]={"type":thinking}
        if thinking!="disabled" and effort in ("low","high","max"):payload["reasoning_effort"]=effort
        client=self._clients.get(api_base)
        timeout_seconds=max(.1,min(float(timeout_seconds or 12),45))
        # A connect timeout occurs before the request is sent. Let deployments
        # tune the first attempt, then allow one short retry before fallback.
        connect_timeout=gateway_connect_timeout(3,timeout_seconds)
        timeout=httpx.Timeout(timeout_seconds,connect=connect_timeout,read=timeout_seconds,write=min(10,timeout_seconds),pool=min(5,timeout_seconds))
        retry_timeout=httpx.Timeout(timeout_seconds,connect=min(3,timeout_seconds),read=timeout_seconds,write=min(10,timeout_seconds),pool=min(5,timeout_seconds))
        if client is None:
            client=httpx.Client(timeout=timeout,limits=httpx.Limits(max_connections=30,max_keepalive_connections=15,keepalive_expiry=120))
            self._clients[api_base]=client
        response=None
        deadline=time.monotonic()+timeout_seconds
        try:
            response=client.post(api_base.rstrip("/")+"/chat/completions",headers=headers,json=payload,timeout=timeout)
        except httpx.ConnectTimeout:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise
            retry_timeout=httpx.Timeout(remaining,connect=min(3,remaining),read=remaining,write=min(10,remaining),pool=min(5,remaining))
            response=client.post(api_base.rstrip("/")+"/chat/completions",headers=headers,json=payload,timeout=retry_timeout)
        if response is None:raise RuntimeError("Dịch vụ LLM không trả response")
        if response.is_error:
            try:detail=response.json().get("error",{}).get("message") or response.text
            except Exception:detail=response.text
            error=RuntimeError(f"Dịch vụ LLM trả lỗi {response.status_code}: {str(detail)[:500]}")
            error.status_code=response.status_code
            raise error
        choice=response.json()["choices"][0]
        if choice.get("finish_reason") in ("length","max_tokens"):
            raise TokenLimitError(f"Model stopped at the token limit ({max_tokens} tokens) before completing its reply")
        content=choice["message"].get("content")
        if isinstance(content,list):content="".join(part.get("text","") for part in content if isinstance(part,dict))
        if not isinstance(content,str) or not content.strip():raise RuntimeError("Model returned an empty response")
        return content.strip()
    def chat_with_meta(self,messages,temperature=.7,max_tokens=350,model=_UNSET_MODEL,fallback_model=_UNSET_MODEL,fallback_model_2=_UNSET_MODEL,profile_mode=None,gateway_timeout_cap_seconds=None,total_budget_seconds=None):
        selected=self.model if model is _UNSET_MODEL else model
        first=self.fallback_model if fallback_model is _UNSET_MODEL else fallback_model
        second=self.fallback_model_2 if fallback_model_2 is _UNSET_MODEL else fallback_model_2
        if not selected:raise RuntimeError("No primary model is assigned to this task in CMS.")
        fallback_messages=([{"role":"system","content":self.fallback_instruction},*messages] if model is _UNSET_MODEL and self.fallback_instruction.strip() else messages)
        candidates=list(dict.fromkeys(value for value in (selected,first,second) if value))
        configured_waits=[max(4,min(45,float(self.model_gateway_timeouts.get(candidate,12)),float(gateway_timeout_cap_seconds or 45))) for candidate in candidates]
        fallback_reserve=12 if len(candidates)>1 else 0
        budget=max(8,min(90,float(os.getenv("LLM_FALLBACK_BUDGET_SECONDS","28"))),max(configured_waits)+fallback_reserve)
        if total_budget_seconds is not None:budget=max(1,min(90,float(total_budget_seconds)))
        started=time.monotonic();errors=[]
        for index,candidate in enumerate(candidates):
            remaining=budget-(time.monotonic()-started)
            if remaining<=0:errors.append("total fallback budget exhausted");break
            try:
                configured=self.model_generation.get(candidate,{}) if profile_mode in ("normal","short") else {}
                prefix="short_" if profile_mode=="short" else ""
                candidate_temperature=float(configured.get(prefix+"temperature",temperature))
                candidate_tokens=max(1,int(configured.get(prefix+"max_tokens",max_tokens)))
                candidate_messages=messages if index==0 else fallback_messages
                gateway_wait=max(4,min(45,float(self.model_gateway_timeouts.get(candidate,12)),float(gateway_timeout_cap_seconds or 45)))
                attempt_timeout=min(gateway_wait,remaining)
                answer=_within_deadline(lambda m=candidate_messages,t=candidate_temperature,n=candidate_tokens,c=candidate,w=attempt_timeout:self._request(m,t,n,c,w),attempt_timeout)
                wire=lambda value:self.model_wire_ids.get(value,value) if value else ""
                return answer,{"primary_model":wire(selected),"primary_model_config_id":selected if selected in self.model_wire_ids else "","fallback_model":wire(first),"fallback_model_2":wire(second),"fallback_used":index>0,"fallback_level":index,"fallback_reason":" | ".join(errors),"actual_model":wire(candidate),"actual_model_config_id":candidate if candidate in self.model_wire_ids else "","thinking_mode":self.model_thinking_modes.get(candidate,"default"),"reasoning_effort":self.model_reasoning_efforts.get(candidate,"default")}
            except Exception as exc:
                status=getattr(exc,"status_code",0)
                retryable=isinstance(exc,(httpx.TransportError,RuntimeError,ValueError)) and (not status or status in (408,409,425,429,500,502,503,504))
                if not retryable:raise
                errors.append(f"{candidate}: {type(exc).__name__}: {str(exc)[:400]}")
        raise RuntimeError("; ".join(errors) or "No configured model available")

    def chat(self,messages,temperature=.7,max_tokens=350,model=_UNSET_MODEL,fallback_model=_UNSET_MODEL,fallback_model_2=_UNSET_MODEL):
        return self.chat_with_meta(messages,temperature,max_tokens,model,fallback_model,fallback_model_2)[0]

    def json(self,messages,schema,model=None,max_tokens=2500):
        prompt={"role":"system","content":"Return ONLY valid JSON matching this schema: "+json.dumps(schema.model_json_schema(),ensure_ascii=False)}
        last_error=None
        for attempt in range(3):
            timeout_seconds=self.model_gateway_timeouts.get(model,12) if model else None
            raw=self._request([prompt,*messages],.1,max_tokens,model,timeout_seconds=timeout_seconds) if model else self.chat([prompt,*messages],temperature=.1,max_tokens=max_tokens)
            try:
                cleaned=re.sub(r"^```(?:json)?\s*|\s*```$","",raw.strip(),flags=re.I)
                try:
                    data=json.loads(cleaned)
                except json.JSONDecodeError:
                    # Some compatible gateways/models wrap a valid object in
                    # prose or Markdown. Decode the first complete JSON object.
                    decoder=json.JSONDecoder()
                    data=None
                    for start,char in enumerate(cleaned):
                        if char!="{":continue
                        try:
                            data,_=decoder.raw_decode(cleaned[start:])
                            break
                        except json.JSONDecodeError:
                            continue
                    if data is None:raise
                return schema.model_validate(data)
            except Exception as exc:
                last_error=exc
                messages=[*messages,{"role":"assistant","content":raw},{"role":"user","content":f"Return a corrected, complete JSON object only. Fix this validation error: {exc}"}]
        raise ValueError(f"LLM returned invalid structured JSON after 3 attempts: {last_error}")

llm=LLM()
