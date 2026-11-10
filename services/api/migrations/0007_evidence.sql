-- VV-010 / VV-024: private evidence objects, access receipts, expiry.
CREATE TABLE evidence (
  tenant_id     text NOT NULL,
  id            text NOT NULL,
  session_id    text NOT NULL,
  attempt_id    text NOT NULL,
  kind          text NOT NULL CHECK (kind IN ('document_front','selfie')),
  storage_key   text NOT NULL UNIQUE,
  digest        text NOT NULL,
  content_type  text NOT NULL,
  size_bytes    integer NOT NULL,
  expires_at    timestamptz NOT NULL,
  deleted_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, attempt_id, kind),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id),
  FOREIGN KEY (tenant_id, attempt_id) REFERENCES attempts(tenant_id, id)
);
CREATE INDEX evidence_expiry_idx ON evidence (expires_at) WHERE deleted_at IS NULL;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON evidence USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant());
CREATE POLICY worker_scan ON evidence FOR SELECT TO vv_worker
  USING (vv_current_tenant() IS NULL AND deleted_at IS NULL AND expires_at < now());
GRANT SELECT, INSERT, UPDATE ON evidence TO vv_app, vv_worker;
