# Asset API and tool validation

Recorded 6 November 2026. The record separates local automated tests from
operator-supplied runtime screenshots. No model calls or changes to the live
deployment were needed to prepare this publication.

## Automated checks

| Suite | Result | Coverage |
| --- | --- | --- |
| Asset API | 14 tests passed | Authentication, A/B scope, denial before SQL, unavailable responses, latest record, null dates, malformed inputs, rejected writes, snapshot checks and sanitised failures |
| Tool client and component source | 12 tests passed | Bounded requests, null preservation, argument checks, error mapping, timeout without retry, malformed/oversized responses, wrong asset/snapshot, redirect refusal, corrected secret-input declaration and in-process API contract |
| Dataset validator | Passed | Canonical document hashes, references, SQL results, database integrity and CSV consistency |

The API and adapter suites ran in the existing Python 3.12 service environment
against the repository publication sources. They generated temporary credentials
and rebuilt temporary databases from committed SQL. The rebuilt byte hash
matched the original frozen snapshot. The adapter tests did not import Langflow
or contact a hosted model. The existing TestClient dependency emits an httpx
deprecation warning; the suites still pass. Dependency migration is separate work.

See the [API](../../services/asset_api/README.md) and
[adapter](../../integrations/langflow/README.md) instructions to reproduce them.

## Runtime observations

| Observation | Evidence | What it establishes |
| --- | --- | --- |
| Standalone tool wiring | `standalone-tool-wiring.png` | Two asset tools connected to the Agent, credential aliases and a three-iteration setting; not a complete schema or network audit |
| A/AHU-01 maintenance answer | `recorded-maintenance-answer.png` | Tool entry, expected date, snapshot date and a visible database reference |
| B/PUMP-01 missing date | `operator-scope-and-null.png` | Tool entry and answer that the next date is not recorded, with snapshot-relative unknown status |
| B flow asked for A records | `operator-scope-and-null.png` | UI reports unavailable after tool execution; raw tool payload and HTTP status are not expanded |
| Attempted administrator instruction | `operator-scope-and-null.png` | Same B conversation reports unavailable for A/AHU-01; not proof of general prompt-injection resistance |
| Missing building | `missing-building-clarification.png` | Assistant asks A or B; no tool entry is visible in the capture |
| Combined database and document answer | `combined-answer.png` | Both named calls show completed and answer contains expected date/notice; exact source citations are not visible |

![B-flow missing-data and cross-scope observations](../images/asset-tools/operator-scope-and-null.png)

The B observations share one conversation. They are useful diagnostics, not
independent trials or a held-out evaluation. API test assertions establish
denial behaviour independently of the screenshots' collapsed tool panels.

![Clarification when the user omits the building](../images/asset-tools/missing-building-clarification.png)

## Publication review

The selected screenshots show credential variable names, not token values.
No visible API keys, bearer tokens, cookies, email addresses or AWS account IDs
were identified. Images retain their original bytes. Generic provider screens,
the default instruction screenshot and redundant component captures were omitted.
Raw flow exports, private identity files, databases and logs were not copied.

The publication source adapts the tested runtime code for repository paths:
`prepare_runtime.py` replaces the setup-specific filename and rebuilds the same
snapshot from SQL. The Compose project and environment names are generic.
The component sources include the confirmed secret-input correction. These
changes do not migrate the running deployment or prove the live editor uses
byte-identical source. The new Compose package needs a deliberate deployment
check before replacing an existing service.

## Remaining checks

- Expand the combined run's payloads and verify exact database `source_refs`
  and supporting SOP chunk identifiers.
- Make the final combined answer visibly cite both sources separately.
- Correlate a returned request ID with the API log for that run.
- Inspect generated tool schemas to confirm credentials never become model arguments.
- Verify document access with distinct controlled identities and inspect
  retrieval payloads; a fixed database token does not establish this boundary.
- Confirm container restart/recreation behaviour for network attachments.
- Run the held-out evaluation separately; do not derive an accuracy percentage
  from these screenshots.

The operator reports successful completion of the implementation. This record
publishes the narrower claims supported by inspected source, automated checks
and the supplied captures. It does not certify production readiness or
multi-user document isolation.
