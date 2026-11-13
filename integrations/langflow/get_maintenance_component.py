"""Bounded client for the local Docker-only asset API. No model or cloud calls."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

API_ORIGIN = 'http://property-asset-api:8000'
MAX_BODY = 65536

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def error(code, retryable=False, request_id=None, trace_id=None):
    return {'status': 'error', 'error': code, 'retryable': retryable,
            'request_id': request_id, 'trace_id': trace_id}

def fetch_asset(building_id, asset_code, token, maintenance=False):
    # No URL, SQL, identity or token is a model-selectable argument.
    if building_id not in ('A', 'B') or not isinstance(asset_code, str) or not re.fullmatch(r'[A-Z][A-Z0-9-]{0,31}', asset_code):
        return error('invalid_arguments')
    if hasattr(token, 'get_secret_value'):
        token = token.get_secret_value()
    if not isinstance(token, str) or not 32 <= len(token) <= 256 or not re.fullmatch(r'[A-Za-z0-9_-]+', token):
        return error('configuration_error')
    suffix = '/maintenance' if maintenance else ''
    url = f'{API_ORIGIN}/v1/assets/{building_id}/{asset_code}{suffix}'
    request = Request(url, headers={'Authorization': 'Bearer ' + token})
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        try:
            response = opener.open(request, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            rid = response.headers.get('X-Request-ID')
            rid = rid if isinstance(rid, str) and re.fullmatch(r'[a-fA-F0-9-]{36}', rid) else None
            tid = response.headers.get('X-Trace-ID')
            tid = tid if isinstance(tid, str) and re.fullmatch(r'[0-9a-f]{32}', tid) else None
            code = response.code
            if code != 200:
                mapping = {400: 'invalid_arguments', 401: 'configuration_error',
                           403: 'unavailable', 404: 'unavailable', 429: 'rate_limited',
                           503: 'service_unavailable'}
                return error(mapping.get(code, 'upstream_error'), code == 429 or code >= 500, rid, tid)
            body = response.read(MAX_BODY + 1)
            if len(body) > MAX_BODY:
                return error('invalid_response', request_id=rid, trace_id=tid)
        data = json.loads(body)
        if not isinstance(data, dict):
            return error('invalid_response', request_id=rid, trace_id=tid)
        asset = data.get('asset')
        expected_id = building_id + '-' + asset_code
        if (data.get('dataset_version') != '1.0.0' or data.get('as_of_date') != '2026-10-26'
            or not isinstance(asset, dict) or asset.get('asset_id') != expected_id
            or asset.get('building_id') != building_id or asset.get('asset_code') != asset_code):
            return error('invalid_response', request_id=rid, trace_id=tid)
        refs = data.get('source_refs')
        if not isinstance(refs, list) or not all(isinstance(r, str) and r.startswith('db://') for r in refs) or 'db://assets/' + expected_id not in refs:
            return error('invalid_response', request_id=rid, trace_id=tid)
        if maintenance:
            record = data.get('maintenance')
            if 'maintenance' not in data or data.get('due_state') not in ('unknown', 'overdue', 'due_today', 'scheduled'):
                return error('invalid_response', request_id=rid, trace_id=tid)
            if record is not None and (not isinstance(record, dict) or record.get('asset_id') != expected_id or 'next_due_date' not in record):
                return error('invalid_response', request_id=rid, trace_id=tid)
        return {'status': 'ok', 'request_id': rid, 'trace_id': tid, 'data': data}
    except (URLError, TimeoutError, ConnectionError, OSError):
        return error('transport_unavailable', retryable=True)
    except (ValueError, UnicodeError, TypeError):
        return error('invalid_response')


# This file is self contained for pasting into the Langflow code editor.
from langflow.custom import Component
from langflow.io import MessageTextInput, SecretStrInput, Output
from langflow.schema import Data

class PropertyGetMaintenance(Component):
    display_name = 'Property Get Latest Maintenance'
    description = 'Get the latest recorded maintenance and next service date for an asset. Requires building A or B and local code such as AHU-01. Null means unknown. Read only.'
    icon = 'Database'
    name = 'PropertyGetMaintenance'
    inputs = [
        MessageTextInput(name='building_id', display_name='Building ID',
                         info='A or B. Ask for clarification if not known.', tool_mode=True),
        MessageTextInput(name='asset_code', display_name='Asset Code',
                         info='Local code such as AHU-01, PUMP-01 or FAN-01.', tool_mode=True),
        SecretStrInput(name='api_token', display_name='Scoped API Credential',
                       required=True,
                       info='Operator credential set by the flow owner. Never model supplied.')]
    outputs = [Output(display_name='Database Result', name='result', method='get_latest_maintenance')]

    def get_latest_maintenance(self) -> Data:
        result = fetch_asset(self.building_id, self.asset_code, self.api_token, maintenance=True)
        data = Data(data=result)
        self.status = data
        return data
