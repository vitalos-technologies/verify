-- M05-T02 evidence deletion lifecycle (VV-009, AT-09).
-- Primary, supplier and backup targets are tracked independently; completion requires all of them.
-- Tombstones persist the minimum needed to re-apply deletion after a backup restore.

CREATE TABLE legal_holds (
  tenant_id   text NOT NULL REFERENCES tenants(id),
  id          text NOT NULL,
  subject_id  text NOT NULL,
  owner       text NOT NULL,
  reason      text NOT NULL,
  expires_at  timestamptz NOT NULL,
  released_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects(tenant_id, id)
);

CREATE TABLE deletion_jobs (
  tenant_id     text NOT NULL REFERENCES tenants(id),
  id            text NOT NULL,
  subject_id    text NOT NULL,
  reason        text NOT NULL,
  controller_authorisation_reference text NOT NULL,
  state         text NOT NULL CHECK (state IN ('requested','on_hold','in_progress','primary_deleted',
                  'awaiting_backup_expiry','complete','error')),
  version       integer NOT NULL DEFAULT 1,
  primary_state text NOT NULL DEFAULT 'pending' CHECK (primary_state IN ('pending','done')),
  backup_expires_at timestamptz,
  requested_by  text NOT NULL,
  last_error    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects(tenant_id, id)
);
CREATE INDEX deletion_jobs_open_idx ON deletion_jobs (updated_at) WHERE state NOT IN ('complete');

CREATE TABLE deletion_supplier_targets (
  tenant_id          text NOT NULL,
  deletion_id        text NOT NULL,
  provider           text NOT NULL,
  provider_reference text NOT NULL,
  state              text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','requested','confirmed','error')),
  receipt            text,
  attempts           integer NOT NULL DEFAULT 0,
  updated_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, deletion_id, provider, provider_reference),
  FOREIGN KEY (tenant_id, deletion_id) REFERENCES deletion_jobs(tenant_id, id)
);

CREATE TABLE deletion_tombstones (
  tenant_id   text NOT NULL REFERENCES tenants(id),
  subject_id  text NOT NULL,
  deletion_id text NOT NULL,
  session_ids text[] NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, subject_id, deletion_id)
);
CREATE TRIGGER tombstones_append_only BEFORE UPDATE OR DELETE ON deletion_tombstones
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();

ALTER TABLE subjects ADD COLUMN deleted_at timestamptz;
ALTER TABLE sessions ADD COLUMN evidence_access_blocked_at timestamptz;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['legal_holds','deletion_jobs','deletion_supplier_targets','deletion_tombstones'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = vv_current_tenant()) '
                   'WITH CHECK (tenant_id = vv_current_tenant())', t);
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE ON legal_holds, deletion_jobs, deletion_supplier_targets TO vv_app, vv_worker;
GRANT SELECT, INSERT ON deletion_tombstones TO vv_app, vv_worker;
CREATE POLICY worker_scan ON deletion_jobs FOR SELECT TO vv_worker USING (state NOT IN ('complete'));

-- Dummy provider (dev/CI mock): asynchronous deletion confirmation.
ALTER TABLE dummy_provider_attempts ADD COLUMN deletion_requested_at timestamptz;
