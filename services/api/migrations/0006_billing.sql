-- M06-T01 usage ledger semantics and invoices (VV-012, AT-12).
-- Billable unit: one completed verification (first approved/declined decision) at the price frozen
-- at reservation. Expired/cancelled/technical-failure sessions are not charged. Credits append.
ALTER TABLE usage_events ADD COLUMN credit_for text;   -- ledger_key of the charge a credit offsets
ALTER TABLE usage_events ADD COLUMN reason text;
ALTER TABLE usage_events ADD COLUMN actor_id text;

CREATE TABLE invoices (
  tenant_id     text NOT NULL REFERENCES tenants(id),
  id            text NOT NULL,
  period        text NOT NULL CHECK (period ~ '^[0-9]{4}-[0-9]{2}$'),
  lines         jsonb NOT NULL,
  total_minor   bigint NOT NULL,
  currency      text NOT NULL DEFAULT 'GBP',
  ledger_digest text NOT NULL,
  issued_by     text NOT NULL,
  issued_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, period)
);
CREATE TRIGGER invoices_append_only BEFORE UPDATE OR DELETE ON invoices
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant());
GRANT SELECT, INSERT ON invoices TO vv_app, vv_worker;
