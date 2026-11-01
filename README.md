# Property Operations RAG Workbench

A local learning project exploring how an AI assistant can answer property
operations questions using fictional documents and structured asset records.
The planned stack combines OpenRAG, Langflow tools, SQLite, OpenTelemetry and
optional LangSmith tracing.

## Current status

**Day 1 repository setup is in progress.** This README establishes the project
scope; it does not claim that the application or its integrations have passed.
Source files and measured results will be added as each lab day is completed.

Only reviewed source files, fictional fixtures and sanitised notes belong in
this repository. Personal lab guides, runtime environments, credentials and raw
evidence are kept outside it. Keep the GitHub repository private until the
Day 7 review of the files and commit history.

## Example use case

> When is Building A's air-handling unit next due for service, and what
> preparation procedure applies?

The assistant should retrieve procedures from documents and obtain the recorded
service date from the asset API. It should cite the evidence and preserve
unknown or unavailable values instead of inventing a date.

## Planned components

| Component | Purpose |
| --- | --- |
| OpenRAG and Docling | Ingest and parse documents for retrieval |
| OpenSearch | Store document chunks and support retrieval |
| Google Drive and Amazon S3 | Hold dedicated fictional source documents |
| Langflow and a hosted OpenAI model | Orchestrate retrieval and tool calls |
| FastAPI and SQLite | Provide validated, read-only asset and maintenance lookups |
| OpenTelemetry Collector and Tempo | Receive and store API server spans |
| Prometheus and Grafana | Collect API metrics and inspect operational signals |
| LangSmith, optional | Inspect Langflow runs with privacy controls |
| Local evaluation helpers | Record human-reviewed answers and coverage gaps |

These are planned components, not a list of completed integrations.

## Lab milestones

| Day | Focus |
| --- | --- |
| 1 | OpenRAG baseline, diagnostic tool and private Git repository |
| 2 | S3 and Drive ingestion, source attribution and retrieval access checks |
| 3 | SQLite-backed asset API and access checks |
| 4 | Langflow tool calling and combined answers |
| 5 | API observability and optional LangSmith tracing |
| 6 | Local human evaluation and a measured improvement |
| 7 | Reproduction checks, documentation and portfolio review |

Target one to ten meaningful commits per lab day, normally two or three.
Daily notes under `docs/daily/` will distinguish executed checks, actual
outcomes, blocked work and next actions. Do not create empty commits to meet a
count or report a planned check as a pass.

## Repository layout

The following layout will be populated during the labs:

```text
README.md                 Project overview and current status
.gitignore                Exclusions for private and generated files
docs/daily/               Sanitised daily progress and result records
tools/                    Reviewed repository support scripts
outputs/                  Selected daily helpers and fictional fixtures
evidence/public/          Reviewed examples, added when appropriate
```

The supplied lab workspace remains separate from this source repository.
Runtime commands should use the working directories specified in the relevant
guide. Do not copy an entire runtime directory into the repository.

## Validation and limitations

No application deployment, ingestion, tool integration or answer-quality result
is claimed by this initial README. Record the exact versions and commands used
when those checks are executed.

The planned asset API uses fixed demonstration credentials with server-defined
building scopes. That does not establish authenticated end-user identity or
building-level document retrieval isolation. Retrieval requires its own tested
boundary before expanding the corpus.

API server tracing and optional LangSmith runs are separate telemetry paths.
The lab associates them manually where verified; it does not automatically
trace every LLM operation or SQLite query end to end. Answer evaluation is local
and human-reviewed.

This is a portfolio learning project, not a production deployment.

## Credentials and budget

- Store manually created credentials in a password manager or a private folder
  outside the repository.
- Keep generated `.env` files, `.secrets/`, identity tokens, virtual environments
  and private evidence out of Git. Ignore rules do not remove tracked files.
- Review the staged diff before every commit and pending commits before pushing.
- Start with the lab's US$10 funding plan. Record measured provider usage
  separately from prepaid credit; actual spending has not been recorded here.
- The US$50 contingency requires a separate review. Git checkpoints require no
  model calls; paid model experiments retain their own budget checks.

## Upstream projects

- [OpenRAG](https://github.com/langflow-ai/openrag)
- [Langflow](https://github.com/langflow-ai/langflow)
- [Docling](https://github.com/docling-project/docling)
- [OpenTelemetry](https://opentelemetry.io/)
- [LangSmith](https://www.langchain.com/langsmith)

Dependencies retain their respective licences. A licence for this repository's
original work has not yet been selected.
