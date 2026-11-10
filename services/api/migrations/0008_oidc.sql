-- M02-T02: OIDC sign-in (authorization code + PKCE), MFA evidence and step-up timestamps.
CREATE TABLE oidc_logins (
  state_hash     text PRIMARY KEY,
  nonce          text NOT NULL,
  verifier_sealed bytea NOT NULL,
  tenant_hint    text,
  return_to      text NOT NULL DEFAULT '/app',
  expires_at     timestamptz NOT NULL,
  used_at        timestamptz
);
GRANT SELECT, INSERT, UPDATE ON oidc_logins TO vv_app;

ALTER TABLE console_sessions ADD COLUMN auth_time timestamptz NOT NULL DEFAULT now();
ALTER TABLE console_sessions ADD COLUMN amr text[] NOT NULL DEFAULT '{}';
ALTER TABLE console_sessions ADD COLUMN auth_method text NOT NULL DEFAULT 'dev';

-- Lookup by verified subject before tenant context exists (one subject may belong to several tenants).
CREATE FUNCTION vv_memberships_for_subject(p_subject text)
RETURNS TABLE (tenant_id text, id text, role text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT m.tenant_id, m.id, m.role FROM memberships m JOIN tenants t ON t.id = m.tenant_id
  WHERE m.user_subject = p_subject AND m.active AND t.status <> 'suspended' ORDER BY m.created_at
$$;
REVOKE ALL ON FUNCTION vv_memberships_for_subject(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_memberships_for_subject(text) TO vv_app;

DROP FUNCTION vv_lookup_console_session(text);
CREATE FUNCTION vv_lookup_console_session(p_token_hash text)
RETURNS TABLE (tenant_id text, id text, membership_id text, csrf_hash text, user_subject text, role text,
               membership_active boolean, revoked_at timestamptz, last_seen_at timestamptz,
               absolute_expires_at timestamptz, tenant_status text, auth_time timestamptz, auth_method text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT s.tenant_id, s.id, s.membership_id, s.csrf_hash, m.user_subject, m.role, m.active,
         s.revoked_at, s.last_seen_at, s.absolute_expires_at, t.status, s.auth_time, s.auth_method
  FROM console_sessions s
  JOIN memberships m ON m.tenant_id = s.tenant_id AND m.id = s.membership_id
  JOIN tenants t ON t.id = s.tenant_id
  WHERE s.token_hash = p_token_hash
$$;
REVOKE ALL ON FUNCTION vv_lookup_console_session(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_lookup_console_session(text) TO vv_app, vv_worker;
