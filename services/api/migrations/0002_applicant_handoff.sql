-- M03-T02 device handoff: a short-lived, one-use token that lets the applicant continue the SAME
-- verification on another device (e.g. desktop -> phone via QR) without creating a new session.
CREATE TABLE applicant_handoffs (
  tenant_id   text NOT NULL,
  id          text NOT NULL,
  session_id  text NOT NULL,
  token_hash  text NOT NULL UNIQUE,
  expires_at  timestamptz NOT NULL,
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);
ALTER TABLE applicant_handoffs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON applicant_handoffs
  USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant());
GRANT SELECT, INSERT, UPDATE ON applicant_handoffs TO vv_app, vv_worker;

CREATE FUNCTION vv_lookup_handoff(p_token_hash text)
RETURNS TABLE (tenant_id text, id text, session_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT tenant_id, id, session_id FROM applicant_handoffs WHERE token_hash = p_token_hash
$$;
REVOKE ALL ON FUNCTION vv_lookup_handoff(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_lookup_handoff(text) TO vv_app;
