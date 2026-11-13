# Langflow asset tools

Two custom components connect the agent to the read-only asset API:

| Component | Action | Model arguments |
| --- | --- | --- |
| Property Get Asset | `get_asset` | `building_id`, `asset_code` |
| Property Get Latest Maintenance | `get_latest_maintenance` | `building_id`, `asset_code` |

The flow owner sets `api_token` through a Credential variable. The model does
not choose the credential, API URL or SQL. The HTTP client fixes the origin at
`http://property-asset-api:8000`, validates arguments, disables proxy use and
redirects, sets a three-second timeout and limits response reads to 64 KiB.
It validates the returned asset, snapshot and database references before
returning `status: ok`. It does not retry failed requests automatically.

## Files

- `tool_client.py`: the bounded HTTP client, independently testable.
- `get_asset_component.py` and `get_maintenance_component.py`: self-contained
  sources for Langflow's custom component editor. Each embeds the same client.
- `test_tool_client.py`: mocked HTTP tests and in-process checks against the real API.
- `copy_demo_token.py`: WSL clipboard helper for the two operator credentials.
- `agent-instructions.md`: database behaviour rules to add to a configured agent.

## Connect the containers

Run in Ubuntu WSL Bash. Find the actual Langflow container before connecting it:

```bash
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}'
read -r -p 'Langflow container ID: ' LF
docker inspect "$LF" --format '{{.Name}} {{.Config.Image}}'
docker exec "$LF" printenv LANGFLOW_ALLOW_CUSTOM_COMPONENTS
docker network connect property-ops-tools "$LF"
```

Confirm the selected container is Langflow and custom components are enabled.
An existing-endpoint message means it is already attached. The API must also
join this network, using alias `property-asset-api`. Langflow keeps its original
network for model access. Manual attachments survive restart but can disappear
when the launcher recreates the container.

## Add and test the components

1. Create two custom components. Paste each complete source file into its own editor.
2. Click Check & Save before enabling Tool Mode.
3. Create Credential variables `PROPERTY_ASSET_A` and `PROPERTY_ASSET_B` using
   privately generated operator tokens. Never place token values in source or prompts.
4. Select one fixed credential on both components in a diagnostic flow.
5. With Tool Mode off, run known inputs directly and inspect Database Result.
6. Clear manual building and asset values. Enable Tool Mode and connect each
   Toolset output to the Agent's Tools input.
7. Inspect the action schemas. Only `building_id` and `asset_code` should be
   model-supplied; neither `api_token` nor an identity selector belongs there.
8. Set editable action names to the values in the table. Keep the iteration
   limit small; the supplied standalone-flow capture shows three.

The supported `SecretStrInput` constructor does not accept `tool_mode=False`.
The corrected sources omit that argument and retain `tool_mode=True` only on
the two `MessageTextInput` fields. The source-contract test checks this distinction.
Actual generated action-schema inspection remains necessary.

To copy a credential without terminal output, after repository runtime preparation:

```bash
export ASSET_RUNTIME="$PWD/runtime/asset-api"
.venv/bin/python integrations/langflow/copy_demo_token.py --credentials "$ASSET_RUNTIME/.secrets/identities.json" --identity operator_a
```

Use `operator_b` for the B diagnostic flow. Paste only into the intended masked
field, then replace the clipboard and remove any saved credential from Windows
clipboard history. The helper does not support `portfolio_admin`. Keep flow
exports private: masked fields do not prove an export contains no secrets.

## Standalone and managed flows

A standalone diagnostic flow connects Chat Input, Agent, the two tools and
Chat Output. Configure its model provider independently; OpenRAG provider setup
does not automatically populate this new flow's model settings. Use fresh
conversations when checking ambiguous identifiers or attempted identity changes.

For the managed OpenRAG flow, add the two custom components directly alongside
retrieval. Do not expose the entire standalone flow as a substitute tool. An
action accepting `input_value` and `session_id` is a different interface from
these components' building and asset arguments.

Preserve the managed flow's runtime model, retrieval and output wiring. Back it
up privately before editing, retain existing retrieval/citation rules and add
the database behaviour rules. Test through OpenRAG, which supplies runtime
values; do not assume the managed flow works in Langflow Playground.

The current managed demonstration uses `PROPERTY_ASSET_A` for both database
tools. Separate operator flows demonstrate fixed credentials, not authenticated
user sessions. Document access needs its own server-enforced design and tests.

## Run the tests

After installing the API requirements in the repository virtual environment:

```bash
.venv/bin/python -m unittest discover -s integrations/langflow -p 'test_tool_client.py' -v
```

The tests use no provider calls and need no real credentials. They exercise
timeouts, error mapping, malformed and oversized responses, redirects, argument
validation, null preservation and the real API contract in process. They do not
prove a live Langflow build, tool schema, model choice or Docker network path.

See the [integration record](../../docs/engineering/asset-tools-integration.md)
and [validation evidence](../../docs/evidence/asset-tools-validation.md).

## API trace correlation

The client and custom components preserve `request_id` and `trace_id` from
the observed API's HTTP response headers, including handled denial responses.
An uninstrumented API can return a null trace ID; a transport failure does not
invent IDs. The credential and URL remain outside model-controlled arguments.
See the [monitoring setup](../../observability/README.md) and
[captured correlation](../../docs/evidence/api-observability.md).
