-- M05-T01 review queue with claim leases, second review for high-impact overrides, and appeals (VV-008).
CREATE TABLE reviews (
  tenant_id        text NOT NULL,
  id               text NOT NULL,
  session_id       text NOT NULL,
  session_version  integer NOT NULL,
  status           text NOT NULL CHECK (status IN ('open','claimed','awaiting_second_review','closed')),
  assignee         text,
  lease_expires_at timestamptz,
  lock_version     integer NOT NULL DEFAULT 1,
  proposal         jsonb,
  proposed_by      text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  closed_at        timestamptz,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);
CREATE UNIQUE INDEX reviews_one_open_per_session ON reviews (tenant_id, session_id) WHERE status <> 'closed';
CREATE INDEX reviews_queue_idx ON reviews (tenant_id, status, created_at);

CREATE TABLE appeals (
  tenant_id          text NOT NULL,
  id                 text NOT NULL,
  session_id         text NOT NULL,
  appealed_revision  integer NOT NULL,
  status             text NOT NULL CHECK (status IN ('open','claimed','resolved')),
  summary            text NOT NULL,
  recorded_by        text NOT NULL,
  assignee           text,
  ack_due_at         timestamptz NOT NULL,
  resolve_due_at     timestamptz NOT NULL,
  resolved_revision  integer,
  created_at         timestamptz NOT NULL DEFAULT now(),
  resolved_at        timestamptz,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);
CREATE UNIQUE INDEX appeals_one_open_per_session ON appeals (tenant_id, session_id) WHERE status <> 'resolved';

ALTER TABLE sessions ADD COLUMN appeal_hold_until timestamptz;

ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE appeals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON reviews USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant());
CREATE POLICY tenant_isolation ON appeals USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant());
GRANT SELECT, INSERT, UPDATE ON reviews, appeals TO vv_app, vv_worker;
