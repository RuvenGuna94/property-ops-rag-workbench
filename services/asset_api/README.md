# Read-only asset API

This FastAPI service exposes two asset lookups over the fictional SQLite
snapshot. It validates a bearer credential and its building scope before
opening a database connection for a business lookup.

| Route | Authentication | Response |
| --- | --- | --- |
| `GET /health` | None | Service status and dataset version |
| `GET /v1/assets/{building}/{code}` | Bearer credential | Asset details and database references |
| `GET /v1/assets/{building}/{code}/maintenance` | Bearer credential | Asset, latest maintenance, next date and snapshot-relative due status |

Business routes reject query parameters. There are no write, bulk-list or
arbitrary-SQL routes. OpenAPI and interactive documentation endpoints are disabled.

## Access and response contract

The local credential file defines three fixed demonstration identities:

| Alias | Allowed buildings |
| --- | --- |
| `operator_a` | A |
| `operator_b` | B |
| `portfolio_admin` | A and B |

Send `Authorization: Bearer <credential>`. Tokens are opaque secrets, not JWTs.
The application compares credentials using `secrets.compare_digest`. Missing
or invalid credentials return HTTP 401. An out-of-scope building and a missing
asset both return HTTP 404 with `{"error":"unavailable"}`. They share a status
and body; this is not a claim of identical timing or complete side-channel resistance.

Successful responses contain `dataset_version`, `as_of_date`, `asset` and
`source_refs`. Maintenance responses also contain `maintenance` and `due_state`.
A null `next_due_date` remains null; the API does not infer a replacement date.
Due status uses the fixed snapshot date, 2026-10-26, rather than the wall clock.

The service opens SQLite with `mode=ro` and `PRAGMA query_only=ON`. Startup
checks the frozen snapshot's byte hash, identity scopes and dataset metadata.
The hash detects mismatch with the reference fixture; it is not a substitute
for protecting code, configuration and host access.

## Reproduce locally

These commands run in Ubuntu WSL Bash from the repository root. Use Python
3.12 to match the tested service environment. The pinned requirements include
the API's test dependencies.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r services/asset_api/requirements.txt
python3 tools/validate_dataset.py
.venv/bin/python services/asset_api/prepare_runtime.py --dataset data --out runtime/asset-api
```

Use an existing suitable virtual environment rather than recreating one you
already depend on. Preparation refuses to overwrite its output directory.
It rebuilds SQLite from `data/database/rebuild.sql`, verifies the original
snapshot hash and generates fresh credentials under the ignored
`runtime/asset-api/.secrets/identities.json`. It never prints token values.
Keep credentials and generated databases out of Git.

SQLite file bytes can depend on the SQLite build. The SQL rebuild matched the
original snapshot in the tested Python 3.12 environment. If the hash differs,
inspect the SQL and SQLite version; do not bypass the check to force startup.

Run the API tests without a live server or provider calls:

```bash
.venv/bin/python -m unittest discover -s services/asset_api -p 'test_api.py' -v
```

Tests create temporary databases and credentials. They cover authentication,
both building scopes, denial before SQL, null dates, latest-record selection,
invalid inputs, rejected writes, snapshot mismatch and sanitised failures.

For host-only development:

```bash
export ASSET_DB="$PWD/runtime/asset-api/data/property_ops.sqlite"
export ASSET_IDENTITIES="$PWD/runtime/asset-api/.secrets/identities.json"
.venv/bin/python -m uvicorn asset_api:create_app --factory --app-dir services/asset_api --host 127.0.0.1 --port 8000 --no-access-log
```

Do not assume this host process is reachable at the Docker service name used
by the Langflow components. Stop it before switching deployment modes.

## Container deployment

The repository Compose file reproduces the private-network design. It uses a
new project name; it does not manage or upgrade an existing runtime deployment.
Do not start a second API with the same network alias while the existing one
is running. Keep the current deployment until you deliberately plan a migration.

For a fresh deployment, create the network if it does not exist:

```bash
docker network create --driver bridge --internal property-ops-tools
```

Verify an existing network instead of recreating it:

```bash
docker network inspect property-ops-tools --format '{{.Internal}} {{.Driver}}'
```

Expect `true bridge`. Start the service from the repository root:

```bash
export ASSET_RUNTIME="$PWD/runtime/asset-api"
export ASSET_UID="$(id -u)"
export ASSET_GID="$(id -g)"
docker compose -f infra/asset-api.compose.yaml config --quiet
docker compose -f infra/asset-api.compose.yaml up -d --build
docker compose -f infra/asset-api.compose.yaml ps
```

The API has no published host port. Its container runs as the selected non-root
UID with read-only mounts, a read-only root filesystem, dropped capabilities,
no new privileges and a temporary `/tmp`. A health check confirms the service
can read the database; it does not test authorization or agent behaviour.

Every response carries a generated `X-Request-ID` and `Cache-Control: no-store`.
The application logs request IDs, route templates, status and duration, not
authorization headers. These JSON logs are implemented; exported OTEL traces
and metrics are separate future work.

## Production limits

Fixed local credentials are not an end-user identity service. This implementation
has no token expiry, OAuth validation, production rate limiter or TLS termination.
The internal Docker network is local containment, not complete host isolation.
Do not expose this service publicly as a production authorization system.

See [the API boundary decision](../../docs/decisions/0001-api-and-database-access.md)
and [the identity decision](../../docs/decisions/0002-fixed-scope-and-user-identity.md).
