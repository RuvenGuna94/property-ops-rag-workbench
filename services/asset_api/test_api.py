"""Deterministic local tests. Uses temporary copies, never edits the source dataset."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from asset_api import create_app, connect_readonly
from prepare_runtime import prepare, SNAPSHOT_SHA256

class AssetAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'runtime'
        prepare(os.environ.get('ASSET_DATASET', str(Path(__file__).resolve().parents[2] / 'data')), self.out)
        self.db = self.out / 'data/property_ops.sqlite'
        self.snapshot = self.db.read_bytes()
        self.keys = self.out / '.secrets/identities.json'
        self.identities = json.loads(self.keys.read_text())
        self.client = TestClient(create_app(self.db, self.keys))
        self.addCleanup(self.client.close)

    def get(self, path, who='operator_a', **kwargs):
        return self.client.get(path, headers={'Authorization': 'Bearer '+self.identities[who]['token']}, **kwargs)

    def test_health_and_no_credentials(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/v1/assets/A/AHU-01').status_code, 401)

    def test_bad_credential(self):
        r = self.client.get('/v1/assets/A/AHU-01', headers={'Authorization': 'Bearer invalid'})
        self.assertEqual((r.status_code, r.json()), (401, {'error':'unauthorized'}))

    def test_asset_scoped_and_provenance(self):
        r = self.get('/v1/assets/A/AHU-01')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['asset']['model'], 'Aster AH-40')
        self.assertEqual(r.json()['source_refs'], ['db://assets/A-AHU-01'])
        self.assertTrue(r.headers['x-request-id'])
        self.assertEqual(r.headers['cache-control'], 'no-store')

    def test_denial_before_database_and_same_as_missing(self):
        with patch('asset_api.connect_readonly', side_effect=AssertionError('Must not query on denial')):
            denied = self.get('/v1/assets/B/AHU-01')
        missing = self.get('/v1/assets/A/UNKNOWN-99')
        self.assertEqual(denied.status_code, 404)
        self.assertEqual((denied.status_code, denied.json()), (missing.status_code, missing.json()))

    def test_reverse_scope(self):
        self.assertEqual(self.get('/v1/assets/A/AHU-01', 'operator_b').status_code, 404)
        self.assertEqual(self.get('/v1/assets/B/AHU-01', 'operator_b').json()['asset']['model'], 'Aster AH-60')

    def test_admin_and_latest_record(self):
        for building, due in [('A', '2026-11-10'), ('B', '2026-11-17')]:
            data = self.get(f'/v1/assets/{building}/AHU-01/maintenance', 'portfolio_admin').json()
            self.assertEqual(data['maintenance']['next_due_date'], due)
            self.assertEqual(data['maintenance']['record_id'], f'MR-{building}-01-03')

    def test_null_and_overdue(self):
        data = self.get('/v1/assets/B/PUMP-01/maintenance', 'operator_b').json()
        self.assertIsNone(data['maintenance']['next_due_date'])
        self.assertEqual(data['due_state'], 'unknown')
        data = self.get('/v1/assets/A/FAN-01/maintenance').json()
        self.assertEqual(data['due_state'], 'overdue')
        self.assertEqual(data['as_of_date'], '2026-10-26')

    def test_identity_spoof_and_sql_shape(self):
        self.assertEqual(self.get('/v1/assets/B/AHU-01?identity=portfolio_admin').status_code, 400)
        self.assertEqual(self.get('/v1/assets/A/AHU-01%27%20OR%201%3D1').status_code, 400)

    def test_post_not_supported(self):
        self.assertEqual(self.client.post('/v1/assets/A/AHU-01', json={'condition':'changed'}).status_code, 405)

    def test_sqlite_write_rejected_and_hash_unchanged(self):
        with closing(connect_readonly(self.db)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("UPDATE assets SET condition='attention_required'")
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), SNAPSHOT_SHA256)

    def test_database_failure_is_sanitized(self):
        with patch('asset_api.connect_readonly', side_effect=sqlite3.OperationalError('PRIVATE PATH')):
            r = self.get('/v1/assets/A/AHU-01')
            self.assertEqual((r.status_code, r.json()), (503, {'error':'service_unavailable'}))
            self.assertNotIn('PRIVATE', r.text)

    def test_missing_database_not_created(self):
        missing = self.out / 'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):
            connect_readonly(missing)
        self.assertFalse(missing.exists())

    def test_prepare_refuses_overwrite(self):
        before = self.keys.read_bytes()
        with self.assertRaises(FileExistsError):
            prepare(os.environ.get('ASSET_DATASET', str(Path(__file__).resolve().parents[2] / 'data')), self.out)
        self.assertEqual(self.keys.read_bytes(), before)

    def test_tampered_snapshot_and_policy_rejected(self):
        self.db.write_bytes(self.db.read_bytes() + b'tamper')
        with self.assertRaises(ValueError):
            create_app(self.db, self.keys)
        self.db.write_bytes(self.snapshot)
        self.identities['operator_a']['allowed_buildings'] = ['A', 'B']
        self.keys.write_text(json.dumps(self.identities))
        with self.assertRaises(ValueError):
            create_app(self.db, self.keys)

if __name__ == '__main__':
    unittest.main(verbosity=2)
