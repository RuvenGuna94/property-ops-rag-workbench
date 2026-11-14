# LangSmith configuration and privacy gate

LangSmith records agent, model and tool runs separately from the API spans in
Tempo. The helper prepares a targeted Compose override for an existing Langflow
service. It does not restart containers, change flows or make model calls.

## Private configuration

Use a tracing-capable key scoped to the intended workspace. Confirm the endpoint
in that workspace's setup screen. Keep the following file outside version control,
under a private runtime directory with mode 700; set the file to mode 600:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=PASTE_KEY_PRIVATELY
LANGSMITH_PROJECT=property-ops-agent
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
LANGSMITH_HIDE_METADATA=true
```

The endpoint above is the default US endpoint. Use the matching regional endpoint
for another workspace. Never place the key in agent instructions, tool arguments,
shell history or a flow export. Review current usage, included allowance, retention
and spend controls before enabling export. A model call has its own provider cost.

## Prepare and apply

From the repository root in WSL, set `LF` to the verified running Langflow container
and `PRIVATE` to an absolute private directory outside the repository:

```bash
umask 077
python3 integrations/langflow/langsmith_override.py --container "$LF" \
  --env-file "$PRIVATE/langsmith.env" \
  --out "$PRIVATE/langsmith.override.yaml"
```

Review the selected service, Compose project and printed APPLY command. Run that
command once only after saving flows. It recreates Langflow with the original
Compose files plus the override. Re-identify the container and restore its manual
`property-ops-tools` network attachment if missing. Check API health from inside
Langflow before running the agent.

The helper accepts only the listed regional HTTPS endpoints, requires all privacy
flags and validates Compose provenance and the Langflow service name. It unsets
legacy project/endpoint aliases and agent-routing variables in this override so
they cannot silently select a different destination. This is not support for
arbitrary self-hosted endpoints.

An existing override is protected. An explicit `--refresh` backs up helper-generated
JSON-form YAML and command files while preserving the original restore command.
Backups also contain secrets and remain private. Do not use refresh to bypass a
provenance or service mismatch. Review the original restore command before running
it to remove this override. Avoid launcher reconfiguration while retaining it.

## Verify actual export

Check only the named tracing/project/privacy variables, SDK version and a boolean
indicating key presence inside the recreated container. Do not dump its environment.
Then execute a standalone Chat Input to Chat Output flow with a harmless unique
canary. If this graph is not traced, diagnose settings before trying one minimal
model call in a tool-free flow. Do not repeatedly spend tokens on unchanged config.

Inspect the new LangSmith run and its children. Input/output canaries must not
appear in uploaded payloads. Inspect metadata and serialized configuration too.
An empty metadata field is not a conclusive test if the flow produced no metadata.
Run names, status and timing may remain visible. If privacy fails, restore the
original configuration and stop property-tool tracing. Environment flags alone
are not evidence that the installed integration honors them.

## Offline checks

```bash
python3 -m unittest discover -s integrations/langflow \
  -p 'test_langsmith_override.py' -v
```

The nine checks mock Docker inspection and use temporary fake credentials. They
cover command generation without secret output, required privacy flags, missing
provenance, endpoint/service validation, conflicting configuration and safe refresh.
They do not prove live export, privacy redaction or billing readiness.

References: [Langflow integration](https://docs.langflow.org/integrations-langsmith),
[LangSmith privacy controls](https://docs.langchain.com/langsmith/mask-inputs-outputs).
