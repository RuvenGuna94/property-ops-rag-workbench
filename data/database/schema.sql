PRAGMA foreign_keys=ON;
CREATE TABLE dataset_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE buildings (building_id TEXT PRIMARY KEY CHECK(building_id IN ('A','B')), name TEXT NOT NULL, timezone TEXT NOT NULL, manager_role TEXT NOT NULL);
CREATE TABLE assets (asset_id TEXT PRIMARY KEY, building_id TEXT NOT NULL REFERENCES buildings(building_id), asset_code TEXT NOT NULL, asset_type TEXT NOT NULL, model TEXT NOT NULL, location TEXT NOT NULL, condition TEXT NOT NULL CHECK(condition IN ('operational','attention_required')), manual_version_id TEXT NOT NULL, UNIQUE(building_id,asset_code));
CREATE TABLE maintenance_records (record_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), performed_on TEXT NOT NULL, status TEXT NOT NULL CHECK(status='completed'), work_order_id TEXT NOT NULL UNIQUE, summary TEXT NOT NULL, next_due_date TEXT);
CREATE INDEX idx_maintenance_asset_date ON maintenance_records(asset_id,performed_on DESC,record_id DESC);
CREATE VIEW current_maintenance AS SELECT m.* FROM maintenance_records m WHERE NOT EXISTS (SELECT 1 FROM maintenance_records newer WHERE newer.asset_id=m.asset_id AND (newer.performed_on>m.performed_on OR (newer.performed_on=m.performed_on AND newer.record_id>m.record_id)));
