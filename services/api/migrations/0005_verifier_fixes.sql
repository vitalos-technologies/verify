-- Fixes from independent verification of 81686a7 (D2, D3, D5, D6).

-- D5: worker queue-scan policies apply only when NO tenant context is set, so inside tenant A's
-- context the worker sees only tenant A rows (policies are OR-combined).
DROP POLICY worker_scan ON outbox;
DROP POLICY worker_scan ON webhook_deliveries;
DROP POLICY worker_scan ON sessions;
DROP POLICY worker_scan ON deletion_jobs;
CREATE POLICY worker_scan ON outbox FOR SELECT TO vv_worker USING (vv_current_tenant() IS NULL);
CREATE POLICY worker_scan ON webhook_deliveries FOR SELECT TO vv_worker USING (vv_current_tenant() IS NULL);
-- D2: expiry also covers sessions stuck in processing/error past their deadline.
CREATE POLICY worker_scan ON sessions FOR SELECT TO vv_worker
  USING (vv_current_tenant() IS NULL AND state IN ('created','in_progress','action_required','processing','error')
         AND expires_at < now());
CREATE POLICY worker_scan ON deletion_jobs FOR SELECT TO vv_worker
  USING (vv_current_tenant() IS NULL AND state NOT IN ('complete'));

-- D5: the API role only inserts provider callbacks; it cannot read other tenants' event metadata.
REVOKE SELECT, UPDATE ON provider_events FROM vv_app;
GRANT SELECT (provider, event_id) ON provider_events TO vv_app;

-- D3: atomic claim of provider events ('processing' with a lease in next_attempt_at).
ALTER TABLE provider_events DROP CONSTRAINT provider_events_processing_state_check;
ALTER TABLE provider_events ADD CONSTRAINT provider_events_processing_state_check
  CHECK (processing_state IN ('pending','processing','processed','quarantined','ignored','retry','failed'));
DROP INDEX provider_events_pending_idx;
CREATE INDEX provider_events_due_idx ON provider_events (next_attempt_at)
  WHERE processing_state IN ('pending','retry','processing');

-- D6: console sessions see tenant status (suspended tenants cannot use the console).
DROP FUNCTION vv_lookup_console_session(text);
CREATE FUNCTION vv_lookup_console_session(p_token_hash text)
RETURNS TABLE (tenant_id text, id text, membership_id text, csrf_hash text, user_subject text, role text,
               membership_active boolean, revoked_at timestamptz, last_seen_at timestamptz,
               absolute_expires_at timestamptz, tenant_status text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT s.tenant_id, s.id, s.membership_id, s.csrf_hash, m.user_subject, m.role, m.active,
         s.revoked_at, s.last_seen_at, s.absolute_expires_at, t.status
  FROM console_sessions s
  JOIN memberships m ON m.tenant_id = s.tenant_id AND m.id = s.membership_id
  JOIN tenants t ON t.id = s.tenant_id
  WHERE s.token_hash = p_token_hash
$$;
REVOKE ALL ON FUNCTION vv_lookup_console_session(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_lookup_console_session(text) TO vv_app, vv_worker;
