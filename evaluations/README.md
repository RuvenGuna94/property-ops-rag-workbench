# Evaluation reference

`cases.jsonl` contains 50 fictional cases with expected answers, evidence
references, expected tools and SQL results where applicable. Each case carries
a development or holdout label. Keep answer keys outside the retrieval corpus,
and do not use holdout answers to tune the agent.

## Fixtures

| Path | Purpose |
| --- | --- |
| `fixtures/superseded_documents/` | Two older preparation procedures for testing revision selection; exclude them from the active corpus. |
| `fixtures/access_expectations.json` | Fictional identity-to-building scopes and expected access decisions. These specify tests, not a runtime policy engine. |

Keep building isolation and authorization cases pending until the application
implements and tests a trusted server-side boundary. A prompt, model refusal
or user-editable search filter does not enforce isolation.

## Offline checks

From the repository root, run `python3 tools/validate_dataset.py`.

The validator checks document hashes, evidence references, expected SQL answers,
database integrity, CSV consistency and asset manual references. It does not
call a model or test live retrieval, connector ownership or authorization.

Use the snapshot date, 2026-10-26, for date-sensitive expected answers. Resolve
all manifest document paths from the repository root. Current sources live
under `data/documents/`; evaluation fixtures stay in this directory.
