# Fictional property operations dataset

Version: 1.0.0. Reference date: 2026-10-26. All business records are fictional.

Cedar Court (Building A) and Maple Exchange (Building B) provide a reproducible
corpus for document retrieval, structured asset lookups and combined answers.

## Contents and ingestion boundaries

- `ingest/s3/`: 10 current service-contract and equipment-manual documents.
- `ingest/google_drive/`: 12 current profiles and operating procedures.
- `archive_do_not_ingest/`: two superseded preparation procedures for revision
  selection checks. Exclude them from the active retrieval corpus.
- `evaluation_do_not_ingest/questions.jsonl`: 50 cases with expected answers,
  evidence references, tool expectations and SQL results. Keep these answers
  outside the retrieval corpus.
- `database/`: two buildings, six assets and 18 maintenance records, supplied
  as CSV, schema SQL and deterministic rebuild SQL for structured lookups.
- `manifest.json`: relative paths, IDs, revisions, effective dates, ingestion
  flags, evidence sections and SHA256 hashes.
- `access_policy.json`: fictional identities and intended building scopes.
  This describes test expectations; it does not enforce access.

Document names and IDs remain stable because evaluations depend on them.
Document bytes are unchanged from the manifest.

## Reproduction

From the repository root, run `python3 tools/validate_dataset.py`.
The validator builds SQLite in memory from `database/rebuild.sql` and checks
the CSV records and evaluation expectations. Generated database binaries and
previously generated validation reports are not committed.

For a persistent local database, execute `database/rebuild.sql` against a new
SQLite database under `runtime/` using your SQLite client. The standalone
`schema.sql` describes the schema; `rebuild.sql` includes schema and seed rows,
so do not execute both against the same database.

The snapshot date is fixed. Interpret dates in evaluation answers against
that snapshot rather than today's date. Offline validation does not establish
ingestion success, model quality, tool execution or building authorization.
