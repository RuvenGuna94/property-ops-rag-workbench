/* OpenRAG 0.8.0 local development only. Paste into DevTools Console while
 * signed into http://localhost:3000. Loading defines helpers; it does not ingest.
 * Publication reconstruction of the browser workflow, not a captured session.
 * Configure credentials privately through OpenRAG before using this script.
 */
(() => {
  if (location.origin !== "http://localhost:3000") {
    throw new Error("Use the authenticated local OpenRAG page on port 3000.");
  }
  const mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  const allowedKeys = ["A", "B"].flatMap(building =>
    ["CON-HVAC", "CON-PUMP", "MAN-AHU", "MAN-FAN", "MAN-PUMP"].map(kind =>
      `property-ops/v1.0.0/Building_${building}/${building}-${kind}-R1.docx`
    )
  );
  const pilotKey = "property-ops/v1.0.0/Building_A/A-CON-HVAC-R1.docx";
  let config = null;
  let plan = null;
  let attempted = false;

  async function request(path, body) {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      headers: body === undefined ? {} : {"Content-Type": "application/json"},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})
    });
    if (!response.ok) {
      throw new Error(`OpenRAG HTTP ${response.status}. Inspect privately; response body not logged.`);
    }
    return response.json();
  }

  async function requireAvailable() {
    const result = await request("/api/connectors");
    if (result.connectors?.aws_s3?.available !== true) {
      throw new Error("Backend S3 connector is unavailable. Check the development override.");
    }
  }

  async function listing() {
    const defaults = await request("/api/connectors/aws_s3/defaults");
    if (defaults.connection_id !== config.connectionId) {
      throw new Error("Connection changed. Initialise again before selecting files.");
    }
    const params = new URLSearchParams({bucket: config.bucket, max_files: "1000"});
    const result = await request(
      `/api/connectors/aws_s3/${encodeURIComponent(config.connectionId)}/browse?${params}`
    );
    // This is a small-corpus workflow. Refuse a potentially truncated listing.
    if (!Array.isArray(result.files) || result.next_page_token || result.files.length >= 1000) {
      throw new Error("Incomplete or oversized listing; do not batch-ingest this selection.");
    }
    for (const key of allowedKeys) {
      const matches = result.files.filter(f => f.bucket === config.bucket && f.key === key);
      if (matches.length !== 1 || !matches[0].id || typeof matches[0].is_ingested !== "boolean") {
        throw new Error(`Missing, ambiguous or incomplete approved object: ${key}`);
      }
    }
    return result.files.filter(f => f.bucket === config.bucket && allowedKeys.includes(f.key));
  }

  window.propertyS3 = {
    async init(bucket) {
      if (typeof bucket !== "string" || !bucket.trim()) throw new Error("Enter the actual bucket name.");
      await requireAvailable();
      const defaults = await request("/api/connectors/aws_s3/defaults");
      if (!defaults.connection_id || !defaults.access_key_set || !defaults.secret_key_set) {
        throw new Error("Create the S3 connection first; credentials stay server-side.");
      }
      config = {bucket: bucket.trim(), connectionId: defaults.connection_id};
      plan = null;
      attempted = false;
      console.info("Ready. Preview the pilot or remaining approved documents.");
    },

    async configure(bucket) {
      // Explicit opt-in mutation: uses credentials already in the backend environment.
      // Never paste AWS keys into this script or Console history.
      if (typeof bucket !== "string" || !bucket.trim()) throw new Error("Enter the actual bucket name.");
      await requireAvailable();
      const defaults = await request("/api/connectors/aws_s3/defaults");
      if (!defaults.access_key_set || !defaults.secret_key_set) throw new Error("Server credentials are missing.");
      await request("/api/connectors/aws_s3/configure", {
        ...(defaults.connection_id ? {connection_id: defaults.connection_id} : {}),
        region: "ap-southeast-1", bucket_names: [bucket.trim()]
      });
      await this.init(bucket);
    },

    async preview(mode = "remaining") {
      if (!config) throw new Error("Call propertyS3.init(actualBucket) first.");
      if (!["pilot", "remaining"].includes(mode)) throw new Error("Use pilot or remaining.");
      if (attempted) throw new Error("A submission was attempted. Inspect tasks before reinitialising.");
      const files = await listing();
      const selected = files.filter(f => !f.is_ingested &&
        (mode === "pilot" ? f.key === pilotKey : f.key !== pilotKey));
      plan = {mode, ids: selected.map(f => f.id)};
      console.table(selected.map(f => ({file: f.name, key: f.key, bytes: f.size})));
      console.info(`${selected.length} approved unindexed file(s) selected. No ingestion submitted.`);
      return selected.length;
    },

    async submit() {
      if (!plan || !config) throw new Error("Preview first.");
      if (attempted) throw new Error("Already attempted. Inspect tasks; do not blindly retry.");
      const files = await listing();
      const selected = files.filter(f => plan.ids.includes(f.id) && !f.is_ingested);
      if (!selected.length) { console.info("No pending selected files."); return; }
      attempted = true; // Retain this guard even if the network fails after acceptance.
      const result = await request("/api/connectors/aws_s3/sync", {
        connection_id: config.connectionId,
        sync_all: false,
        replace_duplicates: false,
        selected_files: selected.map(f => ({
          id: f.id, name: f.name, mimeType: mime, size: f.size,
          modified_time: f.modified_time, isFolder: false
        }))
      });
      console.log(result);
      return result;
    }
  };
  console.info("propertyS3 loaded. No configuration or ingestion has been changed.");
})();
