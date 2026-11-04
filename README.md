# Property Operations RAG Workbench

**Property operations answers backed by documents, asset records and inspectable evidence.**

Property teams work across service contracts, equipment manuals, operating
procedures and maintenance records. Answering a question often means finding
the right document, checking its revision and reconciling it with the recorded
state of an asset.

Property Operations RAG Workbench brings these information sources into a
single question-and-answer workflow. Its design combines retrieval-augmented
generation (RAG) with read-only database tools, operational telemetry and
evidence-based evaluation.

**Status:** Under active development. This repository contains a reproducible
fictional property dataset, offline validation and ingestion inventory tooling.
The asset API and observability stack shown below are planned components; their
implementation and verified results are not yet included.

## The problem in one question

> When is Building A's air-handling unit next due for service, and what
> preparation procedure applies?

A useful answer needs two kinds of evidence:

| Information needed | Source of truth |
| --- | --- |
| The recorded next service date | Structured asset and maintenance records |
| The applicable preparation procedure | The current operating procedure or manual |

The target workflow retrieves the procedure, calls the asset API and assembles
an answer with references to both sources. Missing dates remain unknown, failed
lookups remain visible, and a superseded procedure must not be presented as the
current instruction.

## Design priorities

- **Grounded answers:** retain document citations and database references so a
  reader can inspect the supporting evidence.
- **Controlled tool access:** expose validated asset lookups through an API,
  with server-defined scope and parameterised queries.
- **Honest failure handling:** distinguish missing information, denied access,
  unavailable services and unsupported questions.
- **Observable execution:** investigate API requests through traces, metrics
  and logs, with optional LangSmith visibility into the agent workflow.
- **Measured quality:** assess answer correctness, grounding, citations, tool
  behaviour and scope using a repeatable evaluation process.

## Target architecture

```mermaid
flowchart TD
    S3[Amazon S3] --> Ingest[OpenRAG ingestion and Docling]
    Drive[Google Drive] --> Ingest
    Ingest --> Search[OpenSearch document chunks and vectors]

    User[Operator question] --> App[OpenRAG interface]
    App --> Agent[Langflow agent]
    Agent <--> Model[Hosted OpenAI model]
    Agent --> Retrieval[Document retrieval]
    Retrieval --> Search
    Agent --> Tools[Validated asset tools]
    Tools --> API[FastAPI asset service]
    API --> DB[(SQLite asset and maintenance records)]

    API -->|Server spans| Collector[OpenTelemetry Collector]
    Collector --> Tempo[Tempo]
    API -->|Metrics endpoint scraped| Prometheus[Prometheus]
    Tempo --> Grafana[Grafana]
    Prometheus --> Grafana
    Agent -. Optional workflow traces .-> LangSmith[LangSmith]
```

Document ingestion prepares the retrieval index. Structured lookups happen at
question time through the API. Database facts remain separate from document
knowledge, with each contributing its own evidence to the answer.

The diagram describes the target design. API server spans and LangSmith runs
are separate telemetry paths, associated manually where verified; they do not
form an automatic end-to-end trace of every model operation or database query.

## Technology choices

| Technology | Role and rationale |
| --- | --- |
| OpenRAG, Docling and OpenSearch | Document ingestion, parsing and retrieval |
| Google Drive and Amazon S3 | Separate source repositories for procedures, contracts and manuals |
| Langflow | Visual orchestration and model-visible tool definitions |
| Hosted OpenAI models | Generation and embeddings without running a local model |
| FastAPI and SQLite | A small, deterministic service for read-only operational facts |
| OpenTelemetry, Tempo, Prometheus and Grafana | API request diagnostics and operational visibility |
| LangSmith, optional | Agent workflow inspection with payload privacy controls |

The development environment uses WSL2 and Docker Desktop. The initial design
keeps the database local and stages supporting services to manage memory and
cost on a single machine.

## Evaluation approach

The prepared fictional dataset spans two buildings, with current documents,
archived revisions, asset records and maintenance history. Evaluation scenarios
cover document questions, database questions, combined answers, unavailable
information, access boundaries and service failures.

Answers will be reviewed against source evidence. Reports will distinguish
completed tests from blocked or untested cases, and separate answer quality
from operational health. A successful HTTP request or a visible trace alone
does not establish that an answer is correct.

Measured results and reproduction instructions will be published alongside the
implementation once verified.

## Security and operational scope

All business records are fictional. The intended asset API uses fixed
demonstration credentials with server-defined building scopes. Authenticated
end-user identity propagation and document retrieval authorisation require
separate implementation and verification.

The initial system is read-only. It does not create work orders or permit
model-generated SQL. Credentials, runtime environments and raw evidence stay
outside this source repository; only reviewed source files, fictional fixtures
and sanitised evidence are intended for publication.

## Repository layout

| Path | Purpose |
| --- | --- |
| `data/documents/google_drive/` | 12 current profiles and operating procedures |
| `data/documents/s3/` | 10 current contracts and equipment manuals |
| `data/documents/manifest.json` | Document IDs, revisions, source paths and SHA256 hashes |
| `data/database/` | Fictional asset records in CSV and reproducible SQLite SQL |
| `evaluations/cases.jsonl` | 50 evaluation cases with answers and evidence references |
| `evaluations/fixtures/` | Superseded documents and intended access expectations |
| `tools/` | Offline validation and ingestion inventory commands |

Ingestion selects only current manifest entries under `data/documents/`.
Do not recursively ingest `data/` or the repository. Evaluation fixtures,
expected answers, database records and the manifest itself are not ingestion
inputs. See [the dataset reference](data/README.md) and
[evaluation guidance](evaluations/README.md).

## Run the offline checks

Python 3.10 or later is required. These tools use only the standard library.
Run from the repository root:

```bash
python3 tools/validate_dataset.py
```

The validator checks hashes, evidence references, expected SQL results,
database integrity, CSV consistency and asset manual references. It rebuilds
SQLite in memory, requiring no credentials or running OpenRAG services.
It does not measure model quality or enforce authorization.

Prepare the current documents and a private source inventory:

```bash
python3 tools/ingestion_inventory.py prepare --dataset data/documents --out runtime/ingestion
```

The output directory must not already exist. This creates an upload selection
and `source_ledger.csv`; it does not upload or ingest documents. After recording
ingestion metadata, check the inventory structure with:

```bash
python3 tools/ingestion_inventory.py audit --dataset data/documents --ledger runtime/ingestion/source_ledger.csv
```

The inventory can contain account aliases and provider references, so keep it
under the ignored `runtime/` directory.

## Project foundations

- [OpenRAG](https://docs.openr.ag/)
- [Langflow](https://github.com/langflow-ai/langflow)
- [Docling](https://github.com/docling-project/docling)
- [OpenTelemetry](https://opentelemetry.io/)
- [LangSmith](https://www.langchain.com/langsmith)

Dependencies retain their respective licences. A licence for this repository's
original work has not yet been selected.
