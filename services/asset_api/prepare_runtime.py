"""Stage a verified fictional snapshot and generate local demo credentials once."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile

SNAPSHOT_SHA256 = '7b899fe697560f74421a87e7098635b8a5174742a6c57355964c0780afea010d'
POLICY = {'operator_a': ['A'], 'operator_b': ['B'], 'portfolio_admin': ['A', 'B']}

def prepare(dataset, out):
    dataset, out = Path(dataset).resolve(), Path(out).resolve()
    sql = dataset / 'database/rebuild.sql'
    with tempfile.TemporaryDirectory() as folder:
        rebuilt = Path(folder) / 'property_ops.sqlite'
        with sqlite3.connect(rebuilt) as db:
            db.executescript(sql.read_text(encoding='utf-8'))
        snapshot = rebuilt.read_bytes()
    if hashlib.sha256(snapshot).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError('SQL rebuild differs from the frozen snapshot; inspect SQL and SQLite version.')
    if out.exists():
        raise FileExistsError('Output already exists. Reuse it or choose a new directory.')
    out.mkdir(parents=True)
    (out / 'data').mkdir()
    private = out / '.secrets'
    private.mkdir(mode=0o700)
    (out / 'data/property_ops.sqlite').write_bytes(snapshot)
    credentials = {name: {'token': secrets.token_urlsafe(32), 'allowed_buildings': buildings}
                   for name, buildings in POLICY.items()}
    with (private / 'identities.json').open('x', encoding='utf-8') as stream:
        json.dump(credentials, stream, indent=2)
    os.chmod(private / 'identities.json', 0o600)
    (out / '.gitignore').write_text('.secrets/\ndata/\n.venv/\n__pycache__/\nevidence/private/\n*.log\n', encoding='utf-8')
    (out / 'evidence/private').mkdir(parents=True)
    print('Prepared verified snapshot and three private demo identities. No tokens printed.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    prepare(args.dataset, args.out)
