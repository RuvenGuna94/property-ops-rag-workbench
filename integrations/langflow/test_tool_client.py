"""Offline adapter tests. Mocked HTTP and real asset API in-process checks."""
import ast
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
import tool_client as client

TOKEN = 'test_' + 'x'*40
RID = '11223344-5566-7788-9900-aabbccddeeff'

def payload():
    return {'dataset_version':'1.0.0', 'as_of_date':'2026-10-26',
            'asset':{'asset_id':'A-AHU-01','building_id':'A','asset_code':'AHU-01'},
            'source_refs':['db://assets/A-AHU-01']}

class Response(io.BytesIO):
    def __init__(self, data, code=200):
        super().__init__(data if isinstance(data,bytes) else json.dumps(data).encode())
        self.code=code
        self.headers={'X-Request-ID':RID}

class ToolTests(unittest.TestCase):
    def fetch(self, data, code=200, **kwargs):
        with patch.object(client, 'build_opener') as factory:
            factory.return_value.open.return_value=Response(data,code)
            result=client.fetch_asset('A','AHU-01',TOKEN,**kwargs)
            req=factory.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url, 'http://property-asset-api:8000/v1/assets/A/AHU-01'+('/maintenance' if kwargs.get('maintenance') else ''))
            self.assertEqual(factory.return_value.open.call_args.kwargs['timeout'],3)
            self.assertNotIn(TOKEN,json.dumps(result))
            return result

    def test_success_and_request_id(self):
        result=self.fetch(payload())
        self.assertEqual(result['status'],'ok')
        self.assertEqual(result['request_id'],RID)

    def test_null_preserved(self):
        data=payload()
        data.update(maintenance={'asset_id':'A-AHU-01','next_due_date':None},due_state='unknown')
        result=self.fetch(data,maintenance=True)
        self.assertIsNone(result['data']['maintenance']['next_due_date'])

    def test_reject_model_urls_and_sql_before_network(self):
        with patch.object(client,'build_opener') as factory:
            for b,c in [('A','http://evil'),('B/../../','AHU-01'),('A',"AHU-01' OR 1=1")]:
                self.assertEqual(client.fetch_asset(b,c,TOKEN)['error'],'invalid_arguments')
            factory.assert_not_called()

    def test_missing_or_header_injection_credential(self):
        with patch.object(client,'build_opener') as factory:
            for token in ['',TOKEN+'\r\nX: injected']:
                self.assertEqual(client.fetch_asset('A','AHU-01',token)['error'],'configuration_error')
            factory.assert_not_called()

    def test_status_mapping_sanitized(self):
        for code,expected in [(401,'configuration_error'),(404,'unavailable'),(429,'rate_limited'),(503,'service_unavailable'),(302,'upstream_error')]:
            result=self.fetch({'SECRET':'private stack path'},code)
            self.assertEqual(result['error'],expected)
            self.assertNotIn('SECRET',str(result))

    def test_http_error_path(self):
        with patch.object(client,'build_opener') as factory:
            factory.return_value.open.side_effect=HTTPError('local',404,'hidden',{'X-Request-ID':RID},io.BytesIO(b'private'))
            result=client.fetch_asset('A','AHU-01',TOKEN)
            self.assertEqual(result['error'],'unavailable')
            self.assertNotIn('private',str(result))

    def test_timeout_no_retry(self):
        with patch.object(client,'build_opener') as factory:
            factory.return_value.open.side_effect=URLError('private host detail')
            result=client.fetch_asset('A','AHU-01',TOKEN)
            self.assertEqual(result['error'],'transport_unavailable')
            self.assertTrue(result['retryable'])
            self.assertEqual(factory.return_value.open.call_count,1)

    def test_bad_json_and_oversize(self):
        for data in [b'not json',b'x'*(client.MAX_BODY+1),[],{}]:
            self.assertEqual(self.fetch(data)['error'],'invalid_response')

    def test_wrong_asset_and_wrong_snapshot(self):
        data=payload();data['asset']['asset_id']='B-AHU-01'
        self.assertEqual(self.fetch(data)['error'],'invalid_response')
        data=payload();data['as_of_date']='2099-01-01'
        self.assertEqual(self.fetch(data)['error'],'invalid_response')

    def test_redirect_block(self):
        self.assertIsNone(client.NoRedirect().redirect_request(None,None,302,'',{},'http://elsewhere'))

    def test_component_source_contract(self):
        for name in ['get_asset_component.py','get_maintenance_component.py']:
            source=Path(__file__).with_name(name).read_text()
            ast.parse(source)
            self.assertTrue(source.startswith(Path(client.__file__).read_text()))
            tree=ast.parse(source)
            inputs=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('MessageTextInput','SecretStrInput')]
            fields={next(ast.literal_eval(k.value) for k in n.keywords if k.arg=='name'):next((ast.literal_eval(k.value) for k in n.keywords if k.arg=='tool_mode'), False) for n in inputs}
            self.assertEqual(fields,{'building_id':True,'asset_code':True,'api_token':False})
            secret = next(n for n in inputs if n.func.id == 'SecretStrInput')
            self.assertNotIn('tool_mode', [k.arg for k in secret.keywords])

    def test_real_api_contract_in_process(self):
        sys.path.insert(0,os.environ.get('ASSET_API_HELPERS', str(Path(__file__).resolve().parents[2] / 'services/asset_api')))
        from prepare_runtime import prepare
        from asset_api import create_app
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'runtime'
            prepare(os.environ.get('ASSET_DATASET', str(Path(__file__).resolve().parents[2] / 'data')),out)
            keys=json.loads((out/'.secrets/identities.json').read_text())
            with TestClient(create_app(out/'data/property_ops.sqlite',out/'.secrets/identities.json')) as api:
                def open_request(req,timeout):
                    response=api.get(urlsplit(req.full_url).path,headers=dict(req.header_items()))
                    converted=Response(response.content,response.status_code)
                    converted.headers={'X-Request-ID':response.headers['X-Request-ID']}
                    return converted
                with patch.object(client,'build_opener') as factory:
                    factory.return_value.open.side_effect=open_request
                    a=keys['operator_a']['token']; b=keys['operator_b']['token']
                    good=client.fetch_asset('A','AHU-01',a,True)
                    self.assertEqual(good['data']['maintenance']['next_due_date'],'2026-11-10')
                    self.assertEqual(client.fetch_asset('B','AHU-01',a)['error'],'unavailable')
                    self.assertEqual(client.fetch_asset('A','UNKNOWN-99',a)['error'],'unavailable')
                    null=client.fetch_asset('B','PUMP-01',b,True)
                    self.assertIsNone(null['data']['maintenance']['next_due_date'])

if __name__=='__main__':
    unittest.main(verbosity=2)
