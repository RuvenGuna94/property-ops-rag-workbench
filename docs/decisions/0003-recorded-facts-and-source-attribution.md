# ADR 0003: Keep recorded facts separate from document requirements

Date: 6 November 2026

Status: response contract implemented; combined-answer citation validation remains incomplete.

## Context

An equipment manual may describe a maintenance interval without establishing
the asset's approved next service date. A database record may identify a date
without establishing the occupant-notice requirement in the current SOP.
Using one as a substitute for the other can produce plausible but unsupported answers.

## Decision

Use the asset API for recorded asset and maintenance facts. Use retrieval for
contracts, procedures and manuals. A combined question must execute both paths
and attribute each claim to the source that supports it.

Preserve null next-service dates. Report that the date is not recorded rather
than calculating it from an interval or an older maintenance record. Compute
due status against the dataset snapshot date, not today's date.

Return exact `db://` record references from the API. Preserve OpenRAG's inline
document chunk citations. Request IDs correlate execution with logs; they are
not source citations. A correct-looking final answer does not pass provenance
checks if its supporting payloads or references are missing.

## Consequences

The agent sometimes gives a partial answer. That is preferable to inventing a
date or applying another building's procedure. Tests distinguish missing data,
lookup failures, tool-selection errors, citation omissions and authorization failures.

The current combined screenshot shows both tools completed and the expected
date and notice values. It does not visibly include exact database references
or document citations. Record the integration result and the remaining citation
gap separately; do not publish a complete provenance pass or accuracy percentage.
