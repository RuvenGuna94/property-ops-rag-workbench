# Operating the API monitoring stack

The monitoring stack answers two different questions: Prometheus summarizes
request behaviour over time, while Tempo stores the span for one request.
Grafana provides views over both. Logs remain in Docker; no Loki pipeline is
configured. Agent-level LangSmith tracing remains pending.

## Check from the service outward

Check Compose state, published ports and terminal readiness before diagnosing
the browser. Run from the intended monitoring runtime directory:

```bash
docker compose ps -a
docker compose port grafana 3000
docker compose port prometheus 9090
curl --max-time 20 -fsS http://127.0.0.1:3001/api/health
curl --max-time 10 -fsS http://127.0.0.1:9091/-/ready
```

`3000/tcp` in Docker output alone describes a container port, not a published
host mapping. Grafana should publish `127.0.0.1:3001`; Prometheus should publish
`127.0.0.1:9091`. Do not publish the API or Collector to work around this.

If readiness fails, inspect narrow service logs and resource usage:

```bash
docker compose logs --since 5m --tail 60 grafana
docker stats --no-stream
free -h
```

Review logs privately before publishing. Do not dump container environments,
credentials or unreviewed browser HAR files.

## Resource-pressure investigation

The original Grafana ceiling was 384 MiB. Subsequent measurements recorded
356.3 MiB in use, CPU near 1,394%, about 800 MiB available in WSL and a full
2 GiB swap allocation. Terminal health probes timed out while provisioning
requests and SQLite lock errors also appeared. This established server-side
resource pressure independently of the browser messages.

Recovery used a 1 GiB Grafana trial limit and staged operation: generate traffic
with Grafana stopped, then stop OpenRAG and inspect the stored metrics/traces.
The operator reported recovery. This does not establish that the entire stack
can run together, or identify the exact CPU hot path. Garbage-collection churn
is a possible explanation, not a measured root cause.

Docker CPU percentages can exceed 100% across multiple cores. Cumulative
BLOCK I/O is not a current transfer rate or proof of SSD wear. OOMKilled false
does not rule out memory pressure or swapping.

## Browser errors are symptoms

- A JavaScript ChunkLoadError means an asset request failed or timed out. It
  does not prove Grafana was upgraded or its image is corrupt. Once terminal
  health works, try a hard refresh or private window and inspect the exact
  failed asset's status and timing.
- An import-page provisioning-status error does not prove malformed dashboard
  JSON. Check service responsiveness before changing import methods. The
  repository mentioned by this UI is Grafana provisioning, not this Git repo.
- A CSP warning alone does not establish the source of the failure. Do not add
  unsafe-eval or disable CSP to address a server timeout. Browser-extension
  messages should be distinguished from Grafana's own requests.

The unavailable Collector tag `0.163.0` was replaced with `0.163.2`. The current
configuration disables optional Grafana plugin installation/update checks and
uses SQLite WAL. These changes address separate issues; do not present them as
a single proven cause for every observed failure.

## Inspect metrics

Open Grafana Explore, choose Property Prometheus and Code mode. Run each query
separately. The installed UI runs queries through the blue circular-arrow button.

| Query | Interpretation |
| --- | --- |
| `up{job="property-asset-api"}` | Latest successful scrape is 1; failed scrape is 0 |
| `sum by (status_class) (property_api_requests_total)` | Counts since API-process start, not lifetime totals |
| `sum by (status_class) (rate(property_api_requests_total[5m]))` | Average counter increase per second over five minutes |

For estimated API p95 duration in seconds:

```promql
histogram_quantile(0.95,
  sum by (le) (rate(property_api_duration_seconds_bucket[5m])))
```

Generate requests after the first scrape and wait at least 30 seconds afterward.
Use Range mode and a time range covering the requests. An idle five-minute
window can show a zero rate and NaN p95. Extending the displayed time range
does not extend the query's five-minute calculation window. Sparse requests
and histogram interpolation do not support a performance benchmark.

Import `observability/dashboard.json` as Property API. All four panels use
Prometheus: scrape health, business request rate, estimated API p95 and server
error rate. The dashboard is configuration until its populated live view is
verified. These metrics do not measure LLM latency or model cost.

## Match one request across systems

1. Run the maintenance component directly for A/AHU-01 with the A credential.
2. Retain its actual request_id and trace_id, without the credential.
3. In Grafana Explore, select Property Tempo and look up the 32-character
   trace ID. This installed release accepted the ID in the TraceQL query field.
4. Expand the SERVER span. Compare app.request_id, HTTP status and route with
   the component result and the `asset_api_observed` Docker log entry.
5. Compare durations allowing for display and measurement rounding.

The earlier uninstrumented host server on port 8010 is not needed by this Docker
stack. Stopping that foreground process with Ctrl+C preserves its files and
does not stop Docker. The observed API reads the existing snapshot and credential
files; a running earlier Python process is not a dependency.

## Remaining negative-path evidence

Use the A credential with B/AHU-01 in the direct maintenance component. Expect
unavailable, an API trace with HTTP 404 and a 4xx counter increment, with no B
record returned. Restore blank model arguments and Tool Mode afterward.
Local automated tests cover denial; a matching live denial capture remains
separate evidence. Do not substitute an agent refusal for an executed API check.
