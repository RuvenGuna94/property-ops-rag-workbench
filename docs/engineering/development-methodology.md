# Development methodology

This project uses incremental integration with explicit checks at each boundary.
The aim is to isolate failures before adding another dependency and to keep
claims proportional to the evidence. A plausible answer is not enough: the
underlying lookup, access decision and supporting source must be inspectable.

## Define the contract before connecting the agent

The asset interface started with two business operations: asset details and
latest maintenance. Their contracts define allowed arguments, fixed credential
scope, response fields, source references and failure behaviour. The model does
not receive a general SQL interface or choose its own credential.

The dataset also defines a stable reference point. Its snapshot date, revisions
and document hashes let tests distinguish recorded facts from assumptions.
A missing service date remains null instead of becoming a calculated estimate.

## Test from the data outward

Checks build on smaller, more deterministic parts before involving model behaviour:

| Boundary | Check | What success establishes |
| --- | --- | --- |
| Dataset | Hashes, SQL rebuild, integrity, references and CSV consistency | The fixture is internally consistent and reproducible. |
| API | In-process requests, authentication, scope denial, input validation and read-only access | The service enforces its tested contract without an agent. |
| HTTP client | Mocked timeouts, redirects, error bodies, response limits and malformed payloads | The client handles bounded success and failure cases. |
| Container network | Health, membership and requests from the calling container | The intended caller can reach the service; authorization still needs testing. |
| Custom component | Build, direct execution and generated action-schema inspection | The installed component can call the API with the intended argument interface. |
| Standalone agent | Tool choice, arguments, returned result and final wording | The model can use the tools for the observed requests. |
| Combined agent | Database lookup, retrieved text and separate source citations | Both evidence paths support the combined answer, when all checks pass. |

A check at one layer does not stand in for another. Container health does not
prove credential enforcement. A component's execution time does not prove a
successful lookup. A completed retrieval call does not prove the final answer
cites the right source.

## Exercise failures as part of the interface

The API and client tests cover rejected credentials, cross-building requests,
unknown assets, malformed identifiers, attempted identity overrides, missing
dates, read-only enforcement, unavailable services and invalid responses.

These checks serve different purposes. A null date is a successful lookup with
missing information. An unavailable response is a failed lookup whose wording
does not distinguish an unknown asset from an out-of-scope one. The agent must
preserve that distinction rather than fill either gap with a remembered answer.

The API tests verify scope denial before SQL independently of model behaviour.
A model declining an identity-override request is an observation about that
run; it does not prove the API received and denied a request.

## Diagnose one boundary at a time

When an integration fails, retain the failure and inspect the nearest boundary
before changing prompts or repeating model calls.

- Missing S3 visibility led to source inspection of backend availability and
  frontend rendering conditions. Configured AWS credentials alone did not explain it.
- A component build failure led to inspecting the installed input class. The
  correction removed an unsupported argument from the secret input.
- A nested-flow call exposed text/session arguments instead of building/asset
  arguments. Connecting the custom tools directly corrected the interface.

Keep fixes narrow and reversible. Record version-specific workarounds and
rollback steps. Preserve working flows privately before editing managed wiring.
Do not change credentials, network settings and model instructions together
when a smaller check can distinguish their effects.

## Separate evidence from assumptions

The documentation distinguishes four kinds of support:

- **Inspected implementation:** behaviour visible in the source, such as fixed
  query shapes and the point at which scope checks run.
- **Automated checks:** repeatable assertions with temporary fixtures, generated
  test credentials and mocked or in-process requests.
- **Runtime observations:** selected screenshots of actual tool use and answers.
- **Pending verification:** claims the available payloads, identities or captures
  do not yet establish.

The current suites contain 14 API tests and 12 adapter tests. They are not 26
independent model-quality trials. Runtime prompts are development diagnostics,
not the held-out evaluation, and screenshot timings are not performance benchmarks.

The combined run shows both tools completing, but its final answer lacks visible
exact source citations. Document access isolation also remains unverified.
Those gaps stay open even though the functional integration runs. The result
is a private fixed-scope demonstration, not a certified multi-user deployment.

## Keep iteration inexpensive and reproducible

Use local tests and direct component requests before paid agent runs. Bound
HTTP requests, avoid automatic retries and keep agent iteration limits small.
Check provider usage during live development. These controls reduce unnecessary
calls; they do not constitute an enforced account spending cap.

Commit implementation, tests, architecture decisions and reviewed evidence as
coherent changes. Keep secrets, generated databases, raw logs and flow exports
outside the public source tree. Rebuild runtime data from committed SQL rather
than relying on a developer's local database file.

The published package has passing local checks. Those checks ran manually;
the repository does not yet claim a CI pipeline, a fresh container deployment
of every publication change or formal test-driven development for every feature.

## Extend the same method

For telemetry, first verify API spans and metrics locally, then connect export
and storage, and finally inspect the complete request path. For production
authorization, first define trusted identity propagation, then test service and
retrieval enforcement with distinct identities. Add the integration claim only
after the corresponding boundary has evidence.

Related records:

- [API and database access decision](../decisions/0001-api-and-database-access.md)
- [Fixed scopes and user identity](../decisions/0002-fixed-scope-and-user-identity.md)
- [Source attribution](../decisions/0003-recorded-facts-and-source-attribution.md)
- [S3 investigation](s3-connector-workaround.md)
- [Asset integration](asset-tools-integration.md)
- [Validation evidence](../evidence/asset-tools-validation.md)
