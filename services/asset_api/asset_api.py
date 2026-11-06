"""Local read-only demo API. No arbitrary SQL, cloud calls, or model access."""
from contextlib import closing
from datetime import date
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prepare_runtime import POLICY, SNAPSHOT_SHA256

logger = logging.getLogger('uvicorn.error')
AS_OF = '2026-10-26'

def connect_readonly(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db

def create_app(database=None, credentials=None):
    database = Path(database or os.environ['ASSET_DB']).resolve()
    credential_path = Path(credentials or os.environ['ASSET_IDENTITIES']).resolve()
    if hashlib.sha256(database.read_bytes()).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError('Database hash does not match the frozen project snapshot.')
    identities = json.loads(credential_path.read_text(encoding='utf-8'))
    if set(identities) != set(POLICY):
        raise ValueError('Expected exactly the three demonstration identities.')
    tokens = []
    for name, entry in identities.items():
        token = entry['token']
        if not isinstance(token, str) or len(token) < 32 or not token.isascii():
            raise ValueError('Invalid demo credential.')
        if entry['allowed_buildings'] != POLICY[name]:
            raise ValueError('Identity scope differs from the configured policy.')
        tokens.append(token)
    if len(set(tokens)) != len(tokens):
        raise ValueError('Demo credentials must be unique.')
    with closing(connect_readonly(database)) as db:
        meta = dict(db.execute('SELECT key,value FROM dataset_metadata').fetchall())
        if meta.get('dataset_version') != '1.0.0' or meta.get('as_of_date') != AS_OF:
            raise ValueError('Unexpected dataset metadata.')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed.')

    app = FastAPI(title='Property Operations Asset API', docs_url=None,
                  redoc_url=None, openapi_url=None)

    def fail(status, code):
        return JSONResponse(status_code=status, content={'error': code})

    @app.middleware('http')
    async def evidence(request: Request, call_next):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        response.headers['Cache-Control'] = 'no-store'
        route = request.scope.get('route')
        logger.info(json.dumps({'event': 'asset_api_request', 'request_id': request_id,
                    'method': request.method, 'route': getattr(route, 'path', 'unmatched'),
                    'status': response.status_code,
                    'duration_ms': round((time.perf_counter()-started)*1000, 2)}))
        return response

    @app.get('/health')
    def health():
        try:
            with closing(connect_readonly(database)) as db:
                db.execute('SELECT asset_id FROM assets LIMIT 1').fetchone()
            return {'status': 'ok', 'service': 'asset-api', 'dataset_version': '1.0.0'}
        except sqlite3.Error:
            return fail(503, 'service_unavailable')

    def lookup(request, building, code, maintenance):
        header = request.headers.get('authorization', '')
        if not header.startswith('Bearer '):
            return fail(401, 'unauthorized')
        candidate = header[7:]
        if not candidate.isascii() or len(candidate) > 256:
            return fail(401, 'unauthorized')
        identity = next((entry for entry in identities.values()
                         if secrets.compare_digest(candidate, entry['token'])), None)
        if identity is None:
            return fail(401, 'unauthorized')
        if request.query_params or building not in ('A', 'B') or not re.fullmatch(r'[A-Z][A-Z0-9-]{0,31}', code):
            return fail(400, 'invalid_request')
        # Authorization happens before opening SQLite or looking up an asset.
        if building not in identity['allowed_buildings']:
            return fail(404, 'unavailable')
        try:
            with closing(connect_readonly(database)) as db:
                asset = db.execute('SELECT * FROM assets WHERE building_id=? AND asset_code=?',
                                   (building, code)).fetchone()
                if asset is None:
                    return fail(404, 'unavailable')
                asset = dict(asset)
                refs = ['db://assets/' + asset['asset_id']]
                result = {'dataset_version': '1.0.0', 'as_of_date': AS_OF, 'asset': asset,
                          'source_refs': refs}
                if maintenance:
                    row = db.execute('SELECT * FROM current_maintenance WHERE asset_id=?',
                                     (asset['asset_id'],)).fetchone()
                    if row is None:
                        result.update(maintenance=None, due_state='unknown')
                    else:
                        record = dict(row)
                        due = record['next_due_date']
                        result.update(maintenance=record, due_state=(
                            'unknown' if due is None else 'overdue' if date.fromisoformat(due) < date.fromisoformat(AS_OF)
                            else 'due_today' if due == AS_OF else 'scheduled'))
                        refs.extend(['db://current_maintenance/' + asset['asset_id'],
                                     'db://maintenance_records/' + record['record_id']])
                return result
        except (sqlite3.Error, ValueError):
            return fail(503, 'service_unavailable')

    @app.get('/v1/assets/{building}/{code}')
    def asset(request: Request, building: str, code: str):
        return lookup(request, building, code, False)

    @app.get('/v1/assets/{building}/{code}/maintenance')
    def maintenance(request: Request, building: str, code: str):
        return lookup(request, building, code, True)

    return app
