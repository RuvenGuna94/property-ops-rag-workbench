# Native S3 connector helpers

These helpers support the [OpenRAG 0.8.0 S3 investigation](../../docs/engineering/s3-connector-workaround.md).
They enable a local development path and submit explicit document selections
through OpenRAG's native connector API.

The published helper adapts the local setup script; the browser script
reconstructs the tested workflow. Offline checks cover syntax and browser
selection logic. The published copies have not run against the live deployment.

## Prerequisites

- An existing OpenRAG 0.8.0 Compose deployment with container `tui-backend`.
- Working Google sign-in and AWS reader credentials stored privately in the
  backend environment through the terminal user interface (TUI).
- A private S3 bucket in `ap-southeast-1`. Leave the custom endpoint empty for
  ordinary Amazon S3.
- A reader policy allowing `s3:ListBucket` and `s3:GetBucketLocation` on the
  dedicated bucket ARN, plus `s3:GetObject` on its objects.

Never put AWS keys in source files or browser Console commands.

## Bucket-discovery permission

This release lists buckets when it configures and authenticates a connection.
The reader therefore needs this permission alongside the bucket-scoped policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DiscoverBucketNamesForOpenRAGConnectionTest",
    "Effect": "Allow",
    "Action": "s3:ListAllMyBuckets",
    "Resource": "*"
  }]
}
```

This permission exposes account bucket names; it does not grant access to
their contents. Keep object reads scoped to the dedicated bucket. Do not grant
S3 full access. Use a separate authorized identity to upload fixture documents.

## Enable S3 — Ubuntu WSL Bash

Run from the repository root:

```bash
python3 scripts/s3/control.py enable
```

The helper reads Compose metadata from Docker labels, validates the existing
configuration and backs up `.env`. It then recreates only the backend with
`OPENRAG_DEV_AWS_S3=true`. It does not rebuild images or remove volumes.

The helper retains the original deployment metadata so repeated use does not
stack its own override. It stores all state under `$HOME/openrag-s3-lab`, outside
the repository. That directory includes `.env.before-s3-native`, which contains
credentials. Keep it private.

If you replace the deployment, review the stored metadata before reusing the
helper. Do not delete state to bypass a mismatch. TUI reconfiguration can omit
the override; check availability afterward.

## Connect — browser DevTools Console

Open `http://localhost:3000`, sign in and open DevTools Console. Read
`scripts/s3/browser-ingestion.js`, then paste its contents. Loading the script
defines `propertyS3` without sending requests.

Replace `YOUR_DEDICATED_BUCKET` with your actual bucket name in the examples.
For an existing connection, run:

```javascript
await propertyS3.init("YOUR_DEDICATED_BUCKET");
```

If no connection exists, configure one using credentials already held by the server:

```javascript
await propertyS3.configure("YOUR_DEDICATED_BUCKET");
```

The configure call can update an existing connection's bucket selection and
region. The server resolves the remaining settings. For AWS S3, check that an
earlier custom endpoint is empty before configuring the connection.

## Preview and ingest

The script selects only the ten current contracts and manuals under these keys:

- `property-ops/v1.0.0/Building_A/`
- `property-ops/v1.0.0/Building_B/`

Each prefix contains HVAC and pump contracts and AHU, fan and pump manuals.
The script rejects missing expected objects, oversized listings and pagination
tokens. Use a small dedicated bucket: this release can truncate S3 listings at
the requested limit without returning a continuation token.

For a new deployment, preview and submit the single-document pilot:

```javascript
await propertyS3.preview("pilot");
await propertyS3.submit();
```

Wait for task completion in OpenRAG and confirm that the pilot document shows
Active. A `sync_started` response means the server accepted a job, not that it
finished parsing or indexing.

After the pilot succeeds, reinitialise and preview the remaining documents:

```javascript
await propertyS3.init("YOUR_DEDICATED_BUCKET");
await propertyS3.preview("remaining");
```

Expect at most nine objects. This mode always excludes the pilot,
`A-CON-HVAC-R1.docx`, and skips files the connector marks as ingested.
Review the selection before submitting:

```javascript
await propertyS3.submit();
```

The script refreshes ingestion status before submission and sends only selected
file objects with `sync_all: false` and `replace_duplicates: false`.

After any submission attempt, it blocks another submit in that session. If a
request fails or times out, inspect the task panel before reinitialising; the
server may already have accepted it. This browser guard does not guarantee
server-side idempotency. The upstream browse check can also match by filename,
so keep document filenames unique.

After all tasks finish, initialise and preview again. Expect zero remaining
files. Confirm ten Active S3 documents and twelve Active Drive documents.
Exclude evaluation answers, archives, the manifest and database records from ingestion.

## Disable S3 — Ubuntu WSL Bash

```bash
python3 scripts/s3/control.py disable
```

The helper recreates the backend with the development flag set false. It leaves
data, AWS credentials, stored connections and indexed content in place.

If you retire the connector, review those items separately and remove the
bucket-discovery permission when you no longer need it.
