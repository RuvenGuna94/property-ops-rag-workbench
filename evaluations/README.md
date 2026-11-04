# Evaluation reference

`cases.jsonl` contains 50 fictional cases with expected answers, evidence
references, expected tools and, where applicable, SQL results. Cases carry
development or holdout split labels. Keep answer keys outside the retrieval
corpus; do not use holdout expected answers to tune the agent.

## Fixtures

- `fixtures/superseded_documents/`: two older preparation procedures used to
  check revision selection. They are not part of the active document corpus.
- `fixtures/access_expectations.json`: fictional identity-to-building scopes
  and expected authorization behavior. These are test specifications, not an
  implemented policy engine or runtime authorization configuration.

Building isolation and authorization cases remain pending until a trusted,
server-enforced boundary is implemented and tested. A prompt, model refusal
or user-editable search filter does not establish isolation. Record untested
cases as pending rather than passed.

## Offline checks

From the repository root, run `python3 tools/validate_dataset.py`.
It checks document hashes, evidence references, expected SQL answers,
database integrity, CSV consistency and asset manual references. It neither
calls an LLM nor tests live retrieval, connector ownership or authorization.
The snapshot date is 2026-10-26; use it for date-sensitive expected answers.

All manifest document paths are relative to the repository root. Current
sources live under `data/documents/`; evaluation fixtures stay here.
