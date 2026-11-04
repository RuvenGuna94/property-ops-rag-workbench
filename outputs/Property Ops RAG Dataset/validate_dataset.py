"""Offline consistency checks. No network access and no changes to the dataset."""
from pathlib import Path
import hashlib
import json
import sqlite3

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
docs = manifest['documents']
assert len(docs) == 24
assert sum(d['ingest_default'] for d in docs) == 22
refs = {d['version_id'] + '#' + s for d in docs for s in d['sections']}
for item in docs:
    path = root / item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
database = (root / 'database/property_ops.sqlite').as_uri() + '?mode=ro'
with sqlite3.connect(database, uri=True) as db:
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
    with sqlite3.connect(':memory:') as clone:
        clone.executescript((root / 'database/rebuild.sql').read_text(encoding='utf-8'))
        assert not clone.execute('PRAGMA foreign_key_check').fetchall()
        for table in ('buildings', 'assets', 'maintenance_records', 'dataset_metadata'):
            assert sorted(db.execute(f'SELECT * FROM {table}').fetchall()) == sorted(clone.execute(f'SELECT * FROM {table}').fetchall())
print('PASS: document hashes, evidence references, SQL answers, database integrity and rebuild consistency.')
print('This does not test OpenRAG ingestion, model quality or authorization enforcement.')
