import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
import yaml
from fastapi.testclient import TestClient
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from observed_api import ObservedAPI
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations/langflow'))
import tool_client
from stage_runtime import stage

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'services/asset_api'))
from prepare_runtime import prepare
from asset_api import create_app

class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.runtime=self.root/'day3'
        prepare(REPO / 'data',self.runtime)
        self.keys=json.loads((self.runtime/'.secrets/identities.json').read_text())
        self.exporter=InMemorySpanExporter()
        self.provider=TracerProvider(resource=Resource.create({'service.name':'property-asset-api'}))
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.addCleanup(self.provider.shutdown)
        self.app=ObservedAPI(create_app(self.runtime/'data/property_ops.sqlite',self.runtime/'.secrets/identities.json'),self.provider)
        self.http=TestClient(self.app);self.addCleanup(self.http.close)

    def get(self,path,identity='operator_a'):
        return self.http.get(path,headers={'Authorization':'Bearer '+self.keys[identity]['token']})

    def test_response_and_trace_correlation(self):
        r=self.get('/v1/assets/A/AHU-01/maintenance')
        spans=self.exporter.get_finished_spans()
        self.assertEqual(len(spans),1)
        self.assertEqual(r.headers['x-trace-id'],format(spans[0].context.trace_id,'032x'))
        self.assertEqual(r.headers['x-request-id'],spans[0].attributes['app.request_id'])
        self.assertEqual(r.json()['maintenance']['next_due_date'],'2026-11-10')

    def test_health_and_scrapes_not_business_traffic(self):
        self.http.get('/health');self.http.get('/metrics')
        self.assertEqual(len(self.exporter.get_finished_spans()),0)
        self.assertNotIn('status_class="2xx"',self.http.get('/metrics').text)

    def test_no_secrets_or_raw_paths_in_telemetry(self):
        self.get('/v1/assets/A/AHU-01?private=SECRET_QUERY')
        text=str([dict(s.attributes) for s in self.exporter.get_finished_spans()])+self.http.get('/metrics').text
        for forbidden in ['SECRET_QUERY',self.keys['operator_a']['token'],'A-AHU-01','/A/AHU-01']:
            self.assertNotIn(forbidden,text)
        self.assertIn('http.route',text)

    def test_denied_and_missing_preserved(self):
        a=self.get('/v1/assets/B/AHU-01');b=self.get('/v1/assets/A/UNKNOWN-99')
        self.assertEqual((a.status_code,a.json()),(b.status_code,b.json()))
        self.assertEqual(a.status_code,404)
        self.assertTrue(all(s.status.status_code==StatusCode.UNSET for s in self.exporter.get_finished_spans()))

    def test_server_error_marks_error_span(self):
        import sqlite3
        with patch('asset_api.connect_readonly',side_effect=sqlite3.OperationalError('PRIVATE')):
            r=self.get('/v1/assets/A/AHU-01')
        self.assertEqual(r.status_code,503)
        span=self.exporter.get_finished_spans()[0]
        self.assertEqual(span.status.status_code,StatusCode.ERROR)
        self.assertEqual(span.events,())

    def test_counter_and_duration_low_cardinality(self):
        self.get('/v1/assets/A/AHU-01');self.get('/v1/assets/A/PUMP-01')
        text=self.http.get('/metrics').text
        self.assertIn('property_api_requests_total{method="GET",route="/v1/assets/{building}/{code}",status_class="2xx"} 2.0',text)
        self.assertIn('property_api_duration_seconds_bucket',text)
        self.assertNotIn('request_id=',text)

    def test_bad_token_still_denied(self):
        r=self.http.get('/v1/assets/A/AHU-01',headers={'Authorization':'Bearer bad'})
        self.assertEqual(r.status_code,401)
        self.assertEqual(r.json(),{'error':'unauthorized'})

    def test_tool_client_keeps_both_ids(self):
        class Response(io.BytesIO):
            def __init__(self,r):
                super().__init__(r.content);self.code=r.status_code
                self.headers={'X-Trace-ID':r.headers['x-trace-id'],'X-Request-ID':r.headers['x-request-id']}
        def open_request(req,timeout):
            return Response(self.http.get(urlsplit(req.full_url).path,headers=dict(req.header_items())))
        with patch.object(tool_client,'build_opener') as factory:
            factory.return_value.open.side_effect=open_request
            result=tool_client.fetch_asset('A','AHU-01',self.keys['operator_a']['token'],True)
            self.assertEqual(len(result['trace_id']),32)
            self.assertEqual(len(result['request_id']),36)
            denied=tool_client.fetch_asset('B','AHU-01',self.keys['operator_a']['token'])
            self.assertEqual(denied['error'],'unavailable')
            self.assertEqual(len(denied['trace_id']),32)

    def test_staging_keeps_earlier_sources_unchanged(self):
        source = REPO / 'services/asset_api'
        before = (source / 'asset_api.py').read_bytes()
        out = self.root / 'observed'
        stage(source, self.runtime, out)
        self.assertEqual((source / 'asset_api.py').read_bytes(), before)
        self.assertIn('"tracing": False', (out / 'api-build/asset_api.py').read_text())
        self.assertEqual((out / '.env').stat().st_mode & 0o777, 0o600)
        self.assertEqual((out / '.secrets').stat().st_mode & 0o777, 0o700)
        self.assertFalse((out / '.secrets/identities.json').exists())
        with self.assertRaises(FileExistsError):
            stage(source, self.runtime, out)

    def test_configuration_and_dashboard(self):
        pack=Path(__file__).parent
        for name in ['compose.yaml','collector.yaml','tempo.yaml','prometheus.yaml','datasources.yaml']:
            self.assertIsInstance(yaml.safe_load((pack/name).read_text()),dict)
        compose=yaml.safe_load((pack/'compose.yaml').read_text())
        self.assertNotIn('ports',compose['services']['asset-api'])
        self.assertNotIn('ports',compose['services']['otel-collector'])
        for service in ['grafana','prometheus']:
            self.assertTrue(all(p.startswith('127.0.0.1:') for p in compose['services'][service]['ports']))
            self.assertIn('observe',compose['services'][service]['networks'])
            self.assertIn('dashboard_access',compose['services'][service]['networks'])
        self.assertTrue(compose['networks']['observe']['internal'])
        for service in ['asset-api','otel-collector','tempo']:
            self.assertNotIn('dashboard_access',compose['services'][service]['networks'])
        self.assertEqual(compose['services']['grafana']['environment']['GF_DATABASE_WAL'],'true')
        self.assertEqual(compose['services']['grafana']['mem_limit'],'1g')
        self.assertEqual(compose['services']['grafana']['environment']['GF_PLUGINS_PREINSTALL_DISABLED'],'true')
        self.assertEqual(compose['services']['grafana']['environment']['GF_PLUGINS_PREINSTALL_AUTO_UPDATE'],'false')
        for filename in ['get_asset_component.py','get_maintenance_component.py']:
            import ast
            tree=ast.parse((REPO/'integrations/langflow'/filename).read_text())
            secrets=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='SecretStrInput']
            self.assertEqual(len(secrets),1)
            self.assertNotIn('tool_mode',{k.arg for k in secrets[0].keywords})
        dashboard=json.loads((pack/'dashboard.json').read_text())
        self.assertEqual(len(dashboard['panels']),4)

if __name__=='__main__':unittest.main(verbosity=2)
