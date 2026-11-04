# Fictional property operations dataset

Version: 1.0.0. Reference date: 2026-10-26. All business records are fictional.

The corpus represents Cedar Court (Building A) and Maple Exchange (Building B).
It supports document retrieval, structured asset lookups and combined answers.

## Source documents

`documents/google_drive/` contains 12 current profiles and procedures.
`documents/s3/` contains 10 current contracts and equipment manuals.
Only these 22 current DOCX files are ingestion candidates.

`documents/manifest.json` records IDs, revisions, dates, ingestion eligibility,
evidence sections and SHA256 hashes. Its `path_base` is `repository_root`:
every document path resolves from the directory containing the top-level
README, including references to superseded evaluation fixtures. The manifest
is metadata and must not itself be ingested. Keep document IDs and bytes
stable; evaluations and hashes depend on them.

## Structured records

`database/` contains two buildings, six assets and 18 maintenance records as
CSV plus schema and deterministic rebuild SQL. These are structured lookup
inputs rather than retrieval documents. Run `python3 tools/validate_dataset.py`
from the repository root to rebuild SQLite in memory and check consistency.

For a persistent database, execute `data/database/rebuild.sql` against a new
SQLite database under `runtime/` with your SQLite client. This SQL includes
both schema and seed rows; do not also execute `schema.sql` against it.
Generated databases remain outside version control.

## Evaluation

Expected answers, superseded revisions and access expectations live separately
under [evaluations](../evaluations/README.md). They are not ingestion sources.
Dates in evaluation answers use the fixed snapshot date rather than today.
Offline validation does not establish live ingestion success, model quality,
tool execution or building authorization.
