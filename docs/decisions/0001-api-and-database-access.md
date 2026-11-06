# ADR 0001: Put bounded asset operations behind an API

Date: 6 November 2026

Status: accepted for the local SQLite implementation. Db2 integration is a
production design option, not an implemented component.

## Context

The agent needs current recorded asset and maintenance facts as well as
document evidence. Giving it SQL access would expose more operations and query
choices than the two required lookups. The first implementation uses SQLite,
which has no database user/role/grant system comparable to an enterprise server.

The design question is not whether APIs replace database security. It is where
to restrict business operations and where to enforce data permissions.

## Decision

Expose two read-only operations through FastAPI: asset details and latest
maintenance. Accept building and local asset identifiers, authenticate a fixed
credential, check building scope before SQL, and execute parameterised queries.
Do not expose arbitrary SQL, bulk listing, write operations or a model-selected URL.

Open SQLite read-only, enable query-only mode and mount the database read-only
in the container. Keep database data, API credentials and the hosted-model key
separate. Return stable database references with records so the answer can cite them.

## Why the API remains useful with Db2

An API limits the operations an agent may request; database controls limit the
data and privileges available to the database connection. An enterprise design
can use both. The API provides input validation, bounded response contracts,
request tracing and a place to enforce operation-level policy. Database roles,
views, procedures and row/column controls can provide another boundary.

Db2 supports roles and row/column access control, including row permissions
and column masks. These are database features, not features implemented by this
repository. The exact configuration depends on the customer's Db2 platform,
version, policies and existing applications.
[IBM authorization](https://www.ibm.com/docs/en/db2/12.1?topic=model-authorization),
[IBM RCAC](https://www.ibm.com/docs/en/db2/12.1.0?topic=security-row-column-access-control-rcac).

A shared database account does not automatically represent the human chat
user. A production design must establish a supported trusted identity context
or use restricted service identities with explicit application authorization.
Where supported, Db2 trusted contexts offer a mechanism for controlled
application/user identity handling. That mechanism requires configuration and
tests; it is not an automatic consequence of adding an API.
[IBM trusted-context guidance](https://www.ibm.com/docs/en/db2/11.5.x?topic=ownership-controlling-access-database-administrators-dbas).

The preferred production path is to reuse an approved customer API or service
where it already exposes the required operations. A separate HTTP service is
not mandatory for every workload. Controlled direct access to approved views
or stored procedures can be appropriate when identity, query limits and audit
requirements are satisfied.

## Alternatives considered

| Option | Trade-off |
| --- | --- |
| Agent submits SQL directly | Flexible, but requires controls over query shape, cost, scope and sensitive output. Broader than this workload needs. |
| Database controls alone | Essential with a suitable server, but they do not define the agent's business tool interface. SQLite lacks server-style roles. |
| API checks alone on a broadly privileged database connection | Simple, but an application defect can expose all data available to that connection. Use database least privilege where supported. |
| Bounded API plus database controls | Clear operations and layered enforcement; requires identity design and tests across both layers. |

## Consequences

The service adds deployment and credential-management work. Fixed local tokens
are sufficient for this private demonstration, not for production user management.
SQLite scope enforcement remains in application code. Replacing SQLite with
Db2 would require a driver, query and schema mapping, least-privilege policy,
identity propagation, connection-pool handling and an integration test suite.
The agent-facing tool contract could remain stable if the service preserves it.

The current request IDs and JSON logs support troubleshooting. OTEL export,
rate limiting, token expiry and production transport security remain separate work.
