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

The API suite tests fixed-credential database scopes separately from these
evaluation cases. End-user identity propagation and building-scoped document
retrieval remain pending. A prompt, model refusal or user-editable search filter
does not enforce isolation. Do not mark those cases passed from API tests alone.

See the [asset-tool validation record](../docs/evidence/asset-tools-validation.md)
for the distinction between automated API checks, agent observations and
remaining evidence gaps. These development diagnostics do not count as a
held-out model evaluation or establish an accuracy percentage.

## Offline checks

From the repository root, run `python3 tools/validate_dataset.py`.

The validator checks document hashes, evidence references, expected SQL answers,
database integrity, CSV consistency and asset manual references. It does not
call a model or test live retrieval, connector ownership or authorization.

Use the snapshot date, 2026-10-26, for date-sensitive expected answers. Resolve
all manifest document paths from the repository root. Current sources live
under `data/documents/`; evaluation fixtures stay in this directory.
