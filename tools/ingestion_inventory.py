"""Prepare current documents or audit a manually recorded ledger. No network calls."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

FIELDS = ['version_id','building_id','store','local_sha256','upload_path',
          'provider_ref','provider_version','openrag_document_id','ingesting_identity',
          'ingestion_status','chunk_count','embedding_model','dimensions','evidence_file','notes']


def load_documents(dataset):
    dataset = Path(dataset).resolve()
    manifest = json.loads((dataset / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('path_base') != 'repository_root':
        raise ValueError('Manifest paths must be relative to the repository root.')
    repository = dataset.parents[1]
    if dataset != repository / 'data' / 'documents':
        raise ValueError('Expected the corpus directory at data/documents.')
    if manifest.get('dataset_version') != '1.0.0':
        raise ValueError('This helper expects dataset version 1.0.0.')
    docs = [d for d in manifest['documents'] if d.get('ingest_default')]
    if len(docs) != 22 or len({d['version_id'] for d in docs}) != 22:
        raise ValueError('Expected 22 unique current document versions.')
    counts = {}
    for d in docs:
        if d['status'] != 'current' or d['store'] not in ('s3','google_drive') or d['building_id'] not in ('A','B'):
            raise ValueError('Unexpected status, store or building.')
        source = (repository / d['path']).resolve()
        relative = source.relative_to(dataset)
        expected = Path(d['store']) / ('Building_' + d['building_id'])
        if relative.parent != expected or source.suffix != '.docx':
            raise ValueError('Document path is outside its intended ingestion folder.')
        if source.stem != d['version_id']:
            raise ValueError('Filename and version ID differ.')
        if hashlib.sha256(source.read_bytes()).hexdigest() != d['sha256']:
            raise ValueError('Hash mismatch for ' + d['version_id'])
        key=(d['store'],d['building_id']); counts[key]=counts.get(key,0)+1
    if counts != {('s3','A'):5,('s3','B'):5,('google_drive','A'):6,('google_drive','B'):6}:
        raise ValueError('Unexpected per-store document counts.')
    return dataset, docs


def prepare(dataset, output):
    dataset, docs = load_documents(dataset)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows=[]
    for d in sorted(docs,key=lambda x:x['version_id']):
        source = dataset.parents[1]/d['path']
        relative=Path(d['store'])/('Building_'+d['building_id'])/source.name
        dest=output/'upload_current'/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
        row={f:'' for f in FIELDS}
        row.update(version_id=d['version_id'],building_id=d['building_id'],store=d['store'],
                   local_sha256=d['sha256'],upload_path=('upload_current'/relative).as_posix(),
                   ingestion_status='not_run')
        rows.append(row)
    with (output/'source_ledger.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    print('Prepared 22 current DOCX files: S3 10; Google Drive 12.')
    print('No upload, API call or ingestion was performed.')


def audit(dataset, ledger):
    _,docs=load_documents(dataset); expected={d['version_id']:d for d in docs}
    with Path(ledger).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames != FIELDS: raise ValueError('Ledger columns differ from template.')
        rows=list(reader)
    if len(rows)!=22 or len({r['version_id'] for r in rows})!=22:
        raise ValueError('Expected one ledger row for each of 22 versions.')
    counts={}
    for r in rows:
        d=expected.get(r['version_id'])
        if not d: raise ValueError('Unknown document version.')
        if any(r[k]!=d[k] for k in ['building_id','store']) or r['local_sha256']!=d['sha256']:
            raise ValueError('Source metadata mismatch: '+r['version_id'])
        status=r['ingestion_status'].strip().lower()
        if status not in {'not_run','uploaded','active','failed','blocked','removed'}:
            raise ValueError('Use not_run, uploaded, active, failed, blocked or removed.')
        if status=='active':
            for key in ['provider_ref','openrag_document_id','ingesting_identity','embedding_model','dimensions','evidence_file']:
                if not r[key].strip(): raise ValueError('Active row missing '+key+': '+r['version_id'])
            if int(r['chunk_count'])<1 or int(r['dimensions'])<1:
                raise ValueError('Active row needs positive chunk count and dimensions.')
        counts[status]=counts.get(status,0)+1
    print(json.dumps({'recorded_status_counts':counts,'live_service_checked':False},indent=2))
    print('Ledger structure checked only. Values and access boundaries still need live evidence.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','audit'])
    p.add_argument('--dataset',required=True)
    p.add_argument('--out')
    p.add_argument('--ledger')
    a=p.parse_args()
    try:
        if a.action=='prepare':
            if not a.out: p.error('prepare requires --out')
            prepare(a.dataset,a.out)
        else:
            if not a.ledger: p.error('audit requires --ledger')
            audit(a.dataset,a.ledger)
    except (ValueError,OSError,KeyError) as exc:
        raise SystemExit('STOP: '+str(exc))
