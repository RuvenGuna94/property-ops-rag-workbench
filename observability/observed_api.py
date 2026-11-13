"""Small explicit ASGI telemetry boundary; no request bodies or credentials captured."""
import atexit
import logging
import json
import re
import time
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

log = logging.getLogger('uvicorn.error')

def route_name(path):
    if re.fullmatch(r'/v1/assets/[^/]+/[^/]+/maintenance',path):
        return '/v1/assets/{building}/{code}/maintenance'
    if re.fullmatch(r'/v1/assets/[^/]+/[^/]+',path):
        return '/v1/assets/{building}/{code}'
    return 'unmatched'

class ObservedAPI:
    def __init__(self, app, provider, registry=None):
        self.app=app
        self.provider=provider
        self.tracer=provider.get_tracer('property-ops.asset-api','observed-v1')
        self.registry=registry or CollectorRegistry()
        self.requests=Counter('property_api_requests_total','Business HTTP responses',
                              ['route','method','status_class'],registry=self.registry)
        self.duration=Histogram('property_api_duration_seconds','Business request duration',
                                ['route','method'],buckets=(.005,.01,.025,.05,.1,.25,.5,1,2,5),registry=self.registry)

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':
            return await self.app(scope,receive,send)
        path=scope.get('path','')
        if path=='/metrics':
            if scope.get('method')!='GET':
                await send({'type':'http.response.start','status':405,'headers':[]})
                return await send({'type':'http.response.body','body':b''})
            body=generate_latest(self.registry)
            await send({'type':'http.response.start','status':200,
                        'headers':[(b'content-type',CONTENT_TYPE_LATEST.encode()),(b'cache-control',b'no-store')]})
            return await send({'type':'http.response.body','body':body})
        if path=='/health':
            return await self.app(scope,receive,send)
        route=route_name(path)
        method=scope.get('method','OTHER')
        method=method if method in ('GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS') else 'OTHER'
        started=time.perf_counter()
        code=500
        request_id=None
        with self.tracer.start_as_current_span(method+' '+route,kind=SpanKind.SERVER,
                record_exception=False,set_status_on_exception=False) as span:
            trace_id=format(span.get_span_context().trace_id,'032x')
            span.set_attribute('http.request.method',method)
            span.set_attribute('http.route',route)
            async def traced_send(message):
                nonlocal code,request_id
                if message['type']=='http.response.start':
                    code=message['status']
                    headers=list(message.get('headers',[]))
                    for name,value in headers:
                        if name.lower()==b'x-request-id':
                            candidate=value.decode('ascii',errors='ignore')
                            if re.fullmatch(r'[0-9a-fA-F-]{36}',candidate): request_id=candidate
                    message={**message,'headers':headers+[(b'x-trace-id',trace_id.encode())]}
                await send(message)
            try:
                await self.app(scope,receive,traced_send)
            except Exception:
                span.set_status(Status(StatusCode.ERROR,'application_failure'))
                raise
            finally:
                elapsed=time.perf_counter()-started
                span.set_attribute('http.response.status_code',code)
                if request_id: span.set_attribute('app.request_id',request_id)
                if code>=500: span.set_status(Status(StatusCode.ERROR,'server_error'))
                self.requests.labels(route,method,str(code//100)+'xx').inc()
                self.duration.labels(route,method).observe(elapsed)
                log.info(json.dumps({'event':'asset_api_observed','trace_id':trace_id,
                         'request_id':request_id,'route':route,'status':code,
                         'duration_ms':round(elapsed*1000,2)}))

def create_app():
    from asset_api import create_app as base_app
    provider=TracerProvider(resource=Resource.create({
        'service.name':'property-asset-api','service.version':'observed-v1',
        'deployment.environment.name':'local-lab'}))
    exporter=OTLPSpanExporter(endpoint='http://otel-collector:4318/v1/traces',timeout=2)
    provider.add_span_processor(BatchSpanProcessor(exporter,max_queue_size=256,
                               max_export_batch_size=32,schedule_delay_millis=1000))
    atexit.register(provider.shutdown)
    return ObservedAPI(base_app(),provider)
