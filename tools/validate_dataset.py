"""Offline consistency checks. No network access and no changes to the dataset."""
from pathlib import Path
import csv
import hashlib
import json
import sqlite3

root = Path(__file__).resolve().parents[1] / 'data' / 'property_ops'
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
docs = manifest['documents']
assert len(docs) == 24
assert sum(d['ingest_default'] for d in docs) == 22
refs = {d['version_id'] + '#' + s for d in docs for s in d['sections']}
for item in docs:
    path = root / item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
with sqlite3.connect(':memory:') as db:
    db.executescript((root / 'database/rebuild.sql').read_text(encoding='utf-8'))
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    cases = [json.loads(line) for line in (root / 'evaluation_do_not_ingest/questions.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(cases) == len({c['id'] for c in cases}) == 50
    for case in cases:
        for ref in case['evidence_refs']:
            if not ref.startswith('db://'):
                assert ref in refs, ref
            else:
                table, key = ref[5:].split('/')
                assert table in ('assets', 'current_maintenance')
                assert db.execute(f'SELECT COUNT(*) FROM {table} WHERE asset_id=?', (key,)).fetchone()[0] == 1
        if case['sql']:
            assert case['sql'].startswith('SELECT ')
            assert [list(r) for r in db.execute(case['sql'], case['sql_params'])] == case['expected_db_rows'], case['id']
    for table in ('buildings', 'assets', 'maintenance_records'):
        with (root / 'database' / (table + '.csv')).open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            assert columns and all(c.replace('_', '').isalnum() for c in columns)
            expected = sorted(tuple(row[c] or None for c in columns) for row in reader)
        actual = sorted(db.execute('SELECT ' + ','.join(columns) + ' FROM ' + table).fetchall())
        assert actual == expected, table
    for (manual,) in db.execute('SELECT manual_version_id FROM assets'):
        assert any(d['version_id'] == manual and d['status'] == 'current' for d in docs), manual
print('PASS: document hashes, evidence references, SQL answers, SQL rebuild integrity, CSV consistency and asset manual references.')
print('This does not test OpenRAG ingestion, model quality or authorization enforcement.')
