# Fictional property operations dataset

Version 1.0.0 · Reference date: 2026-10-26

The dataset represents Cedar Court (Building A) and Maple Exchange (Building B).
All business records are fictional. Use the documents for retrieval and the
structured records for asset lookups.

## Documents to ingest

| Directory | Contents |
| --- | --- |
| `documents/google_drive/` | 12 current profiles and operating procedures |
| `documents/s3/` | 10 current contracts and equipment manuals |

Only these 22 current DOCX files belong in the active retrieval corpus.

`documents/manifest.json` records document IDs, revisions, dates, ingestion
eligibility, evidence sections and SHA256 hashes. Its `path_base` is
`repository_root`: resolve every document path from the repository root,
including references to superseded evaluation fixtures.

Keep document IDs and file bytes stable; hashes and evaluation references
depend on them. Do not ingest the manifest.

## Asset and maintenance records

`database/` contains CSV records for two buildings, six assets and 18
maintenance records, plus schema and SQL to rebuild SQLite. Query these records
through structured lookups rather than adding them to the document index.

From the repository root, run `python3 tools/validate_dataset.py` to rebuild
SQLite in memory and check the dataset.

To create a persistent database, execute `data/database/rebuild.sql` against
a new SQLite database under the ignored `runtime/` directory. Use your SQLite
client. The script includes the schema and seed records, so do not also run
`schema.sql` against that database. Keep generated databases out of Git.

## Evaluation fixtures

The [evaluation directory](../evaluations/README.md) holds expected answers,
superseded procedures and access expectations. Keep them outside the retrieval
corpus. Date-sensitive answers use the fixed reference date, not today's date.

Offline validation checks dataset consistency. It does not test live ingestion,
model quality, tool execution or building authorization.
