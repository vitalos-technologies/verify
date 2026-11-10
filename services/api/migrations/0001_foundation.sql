-- Vitalos Verify foundation schema (M02-M04 prototype).
-- Applied by the migration/owner role. Runtime roles (vv_app, vv_worker) are
-- NOT owners, so row-level security applies to them. Lookups that must happen
-- before tenant context is known go through narrow SECURITY DEFINER functions.
-- Requirements: VV-001, VV-002, VV-003, VV-005, VV-006, VV-007, VV-011, VV-015, VV-023.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tenant context helper. Missing context yields NULL, which matches nothing.
CREATE FUNCTION vv_current_tenant() RETURNS text
  LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.tenant_id', true), '') $$;

-- Generic append-only guard.
CREATE FUNCTION vv_forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'append-only table %: % not permitted', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'insufficient_privilege';
END $$;

-- ---------------------------------------------------------------- tenancy
CREATE TABLE tenants (
  id                    text PRIMARY KEY,
  name                  text NOT NULL,
  status                text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','billing_hold')),
  region_policy         text[] NOT NULL DEFAULT ARRAY['synthetic'],
  retention_profile     text NOT NULL DEFAULT 'pilot_proposed_30d',
  monthly_session_cap   integer NOT NULL DEFAULT 100 CHECK (monthly_session_cap >= 0),
  daily_message_cap     integer NOT NULL DEFAULT 50 CHECK (daily_message_cap >= 0),
  created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  tenant_id      text NOT NULL REFERENCES tenants(id),
  id             text NOT NULL,
  user_subject   text NOT NULL,
  role           text NOT NULL CHECK (role IN ('owner','administrator','reviewer','developer','auditor')),
  active         boolean NOT NULL DEFAULT true,
  revoked_at     timestamptz,
  revoked_reason text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, user_subject)
);

CREATE TABLE console_sessions (
  tenant_id       text NOT NULL,
  id              text NOT NULL,
  membership_id   text NOT NULL,
  token_hash      text NOT NULL UNIQUE,
  csrf_hash       text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  last_seen_at    timestamptz NOT NULL DEFAULT now(),
  absolute_expires_at timestamptz NOT NULL,
  revoked_at      timestamptz,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, membership_id) REFERENCES memberships(tenant_id, id)
);

CREATE TABLE api_keys (
  tenant_id      text NOT NULL REFERENCES tenants(id),
  id             text NOT NULL,
  prefix         text NOT NULL UNIQUE,
  secret_hash    text NOT NULL,
  scopes         text[] NOT NULL,
  label          text NOT NULL DEFAULT '',
  created_by     text,
  expires_at     timestamptz,
  revoked_at     timestamptz,
  revoked_reason text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id)
);

CREATE TABLE idempotency_keys (
  tenant_id       text NOT NULL REFERENCES tenants(id),
  operation       text NOT NULL,
  key             text NOT NULL,
  request_digest  text NOT NULL,
  response_status integer,
  response_sealed bytea,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, operation, key)
);

-- ---------------------------------------------------------------- policies
CREATE TABLE policies (
  tenant_id     text NOT NULL REFERENCES tenants(id),
  id            text NOT NULL,              -- version-specific row id
  key           text NOT NULL,              -- e.g. workforce_identity
  version       integer NOT NULL CHECK (version >= 1),
  status        text NOT NULL CHECK (status IN ('draft','validated','published','retired')),
  definition    jsonb NOT NULL,
  definition_digest text NOT NULL,
  validation_report jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  published_at  timestamptz,
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, key, version)
);

CREATE FUNCTION vv_policy_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' AND OLD.status IN ('published','retired') THEN
    RAISE EXCEPTION 'published policy versions cannot be deleted' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF TG_OP = 'UPDATE' AND OLD.status IN ('published','retired') THEN
    IF NEW.definition IS DISTINCT FROM OLD.definition
       OR NEW.definition_digest IS DISTINCT FROM OLD.definition_digest
       OR NEW.version IS DISTINCT FROM OLD.version OR NEW.key IS DISTINCT FROM OLD.key
       OR NOT (NEW.status = OLD.status OR (OLD.status = 'published' AND NEW.status = 'retired')) THEN
      RAISE EXCEPTION 'published policy versions are immutable' USING ERRCODE = 'insufficient_privilege';
    END IF;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER policies_immutable BEFORE UPDATE OR DELETE ON policies
  FOR EACH ROW EXECUTE FUNCTION vv_policy_immutable();

-- ---------------------------------------------------------------- sessions
CREATE TABLE subjects (
  tenant_id          text NOT NULL REFERENCES tenants(id),
  id                 text NOT NULL,
  external_reference text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, external_reference)
);

CREATE TABLE sessions (
  tenant_id          text NOT NULL,
  id                 text NOT NULL,
  subject_id         text NOT NULL,
  policy_row_id      text NOT NULL,
  policy_key         text NOT NULL,
  policy_version     integer NOT NULL,
  external_reference text NOT NULL,
  country            text NOT NULL,
  document_type      text NOT NULL,
  coverage_version   text NOT NULL,
  coverage_entry_id  text NOT NULL,
  provider           text NOT NULL,
  state              text NOT NULL CHECK (state IN ('created','in_progress','processing','approved','declined',
                        'review_required','action_required','expired','cancelled','error')),
  version            integer NOT NULL DEFAULT 1,
  quality_retries_used integer NOT NULL DEFAULT 0,
  hosted_token_hash  text UNIQUE,
  hosted_token_expires_at timestamptz,
  hosted_token_used_at timestamptz,
  expires_at         timestamptz NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, subject_id) REFERENCES subjects(tenant_id, id),
  FOREIGN KEY (tenant_id, policy_row_id) REFERENCES policies(tenant_id, id)
);
CREATE INDEX sessions_list_idx ON sessions (tenant_id, created_at DESC, id DESC);
CREATE INDEX sessions_expiry_idx ON sessions (expires_at) WHERE state IN ('created','in_progress','action_required');

CREATE TABLE applicant_sessions (
  tenant_id     text NOT NULL,
  id            text NOT NULL,
  session_id    text NOT NULL,
  token_hash    text NOT NULL UNIQUE,
  expires_at    timestamptz NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);

CREATE TABLE notice_acknowledgements (
  tenant_id      text NOT NULL,
  id             text NOT NULL,
  session_id     text NOT NULL,
  notice_version text NOT NULL,
  kind           text NOT NULL CHECK (kind IN ('acknowledgement','explicit_consent')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, session_id, notice_version, kind),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);

CREATE TABLE attempts (
  tenant_id          text NOT NULL,
  id                 text NOT NULL,
  session_id         text NOT NULL,
  sequence           integer NOT NULL,
  provider           text NOT NULL,
  provider_reference text,
  state              text NOT NULL CHECK (state IN ('creating','capturing','submitted','completed','superseded','error')),
  created_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, session_id, sequence),
  UNIQUE (provider, provider_reference),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);

CREATE TABLE checks (
  tenant_id        text NOT NULL,
  id               text NOT NULL,
  session_id       text NOT NULL,
  attempt_id       text,
  type             text NOT NULL CHECK (type IN ('government_id','face_match','liveness','email','phone',
                     'document','database','nfc','age','digital_id')),
  result           text NOT NULL CHECK (result IN ('pass','fail','inconclusive','error','not_run')),
  reasons          text[] NOT NULL DEFAULT '{}',
  provider         text NOT NULL,
  provider_version text,
  model_version    text,
  score            numeric,
  score_type       text,
  observation_id   text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, session_id, observation_id, type),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id),
  FOREIGN KEY (tenant_id, attempt_id) REFERENCES attempts(tenant_id, id)
);
CREATE TRIGGER checks_append_only BEFORE UPDATE OR DELETE ON checks
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();

CREATE TABLE decisions (
  tenant_id      text NOT NULL,
  id             text NOT NULL,
  session_id     text NOT NULL,
  revision       integer NOT NULL CHECK (revision >= 1),
  outcome        text NOT NULL CHECK (outcome IN ('approved','declined','review_required','action_required')),
  actor_type     text NOT NULL CHECK (actor_type IN ('policy_engine','reviewer')),
  actor_id       text NOT NULL,
  method         text NOT NULL CHECK (method IN ('automated','evidence_review','alternative_method')),
  reason_codes   text[] NOT NULL DEFAULT '{}',
  reason_text    text,
  policy_row_id  text NOT NULL,
  policy_key     text NOT NULL,
  policy_version integer NOT NULL,
  evidence_check_ids text[] NOT NULL DEFAULT '{}',
  trace          jsonb NOT NULL,
  supersedes_revision integer,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, session_id, revision),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id),
  FOREIGN KEY (tenant_id, policy_row_id) REFERENCES policies(tenant_id, id)
);
CREATE TRIGGER decisions_append_only BEFORE UPDATE OR DELETE ON decisions
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();

-- ---------------------------------------------------------------- contact checks (VV-015)
CREATE TABLE contact_challenges (
  tenant_id        text NOT NULL,
  id               text NOT NULL,
  session_id       text NOT NULL,
  channel          text NOT NULL CHECK (channel IN ('email','phone')),
  destination_hash text NOT NULL,
  code_hash        text NOT NULL,
  expires_at       timestamptz NOT NULL,
  failed_attempts  integer NOT NULL DEFAULT 0,
  consumed_at      timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id)
);
CREATE INDEX contact_challenges_session_idx ON contact_challenges (tenant_id, session_id, created_at);
CREATE INDEX contact_challenges_dest_idx ON contact_challenges (tenant_id, destination_hash, created_at);

-- ---------------------------------------------------------------- provider events (no tenant until resolved)
CREATE TABLE provider_events (
  provider         text NOT NULL,
  event_id         text NOT NULL,
  provider_reference text NOT NULL,
  tenant_id        text,
  session_id       text,
  received_at      timestamptz NOT NULL DEFAULT now(),
  processing_state text NOT NULL DEFAULT 'pending'
                   CHECK (processing_state IN ('pending','processed','quarantined','ignored','retry','failed')),
  attempts         integer NOT NULL DEFAULT 0,
  next_attempt_at  timestamptz NOT NULL DEFAULT now(),
  raw_body         bytea,
  raw_expires_at   timestamptz NOT NULL DEFAULT now() + interval '7 days',
  outcome_note     text,
  PRIMARY KEY (provider, event_id)
);
CREATE INDEX provider_events_pending_idx ON provider_events (next_attempt_at) WHERE processing_state IN ('pending','retry');

-- ---------------------------------------------------------------- usage ledger
CREATE TABLE usage_events (
  tenant_id    text NOT NULL REFERENCES tenants(id),
  id           text NOT NULL,
  session_id   text,
  ledger_key   text NOT NULL,
  charge_type  text NOT NULL CHECK (charge_type IN ('reservation','reservation_release','completed_verification','message','credit')),
  quantity     integer NOT NULL DEFAULT 1,
  amount_minor bigint NOT NULL,
  currency     text NOT NULL DEFAULT 'GBP',
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, ledger_key)
);
CREATE TRIGGER usage_append_only BEFORE UPDATE OR DELETE ON usage_events
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();

-- ---------------------------------------------------------------- events and webhooks (VV-011)
CREATE TABLE outbox (
  tenant_id        text NOT NULL REFERENCES tenants(id),
  id               text NOT NULL,
  event_type       text NOT NULL,
  resource_id      text NOT NULL,
  resource_version integer NOT NULL,
  payload          jsonb NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  dispatched_at    timestamptz,
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX outbox_pending_idx ON outbox (created_at) WHERE dispatched_at IS NULL;

CREATE TABLE webhook_endpoints (
  tenant_id     text NOT NULL REFERENCES tenants(id),
  id            text NOT NULL,
  url           text NOT NULL,
  events        text[] NOT NULL,
  secrets_sealed bytea NOT NULL,
  status        text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','quarantined')),
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id)
);

CREATE TABLE webhook_deliveries (
  tenant_id       text NOT NULL,
  id              text NOT NULL,
  event_id        text NOT NULL,
  endpoint_id     text NOT NULL,
  attempt         integer NOT NULL DEFAULT 0,
  state           text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','delivered','failed','blocked')),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  last_status     integer,
  last_error      text,
  delivered_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, event_id, endpoint_id),
  FOREIGN KEY (tenant_id, event_id) REFERENCES outbox(tenant_id, id),
  FOREIGN KEY (tenant_id, endpoint_id) REFERENCES webhook_endpoints(tenant_id, id)
);
CREATE INDEX webhook_deliveries_due_idx ON webhook_deliveries (next_attempt_at) WHERE state = 'pending';

-- ---------------------------------------------------------------- audit (VV-010 groundwork)
CREATE TABLE audit_events (
  tenant_id   text NOT NULL REFERENCES tenants(id),
  id          text NOT NULL,
  actor_type  text NOT NULL,
  actor_id    text NOT NULL,
  action      text NOT NULL,
  object_type text NOT NULL,
  object_id   text NOT NULL,
  reason      text,
  request_id  text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, id)
);
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION vv_forbid_mutation();

-- ---------------------------------------------------------------- rate limits (not tenant data)
CREATE TABLE rate_limit_windows (
  bucket       text NOT NULL,
  window_start timestamptz NOT NULL,
  count        integer NOT NULL DEFAULT 0,
  PRIMARY KEY (bucket, window_start)
);

-- ---------------------------------------------------------------- dummy provider state
-- Simulates the remote state of an external supplier for development and CI only.
-- It is NOT a real provider and holds only synthetic scenario names.
CREATE TABLE dummy_provider_attempts (
  provider_reference text PRIMARY KEY,
  capture_token_hash text NOT NULL UNIQUE,
  idempotency_key    text NOT NULL UNIQUE,
  scenario           text,
  status             text NOT NULL DEFAULT 'awaiting_capture',
  created_at         timestamptz NOT NULL DEFAULT now(),
  completed_at       timestamptz
);
CREATE TABLE dummy_messages (
  id          text PRIMARY KEY,
  channel     text NOT NULL,
  destination_hash text NOT NULL,
  template    text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- row-level security
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['tenants','memberships','console_sessions','api_keys','idempotency_keys','policies',
    'subjects','sessions','applicant_sessions','notice_acknowledgements','attempts','checks','decisions',
    'contact_challenges','usage_events','outbox','webhook_endpoints','webhook_deliveries','audit_events']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    IF t = 'tenants' THEN
      EXECUTE 'CREATE POLICY tenant_isolation ON tenants USING (id = vv_current_tenant()) WITH CHECK (id = vv_current_tenant())';
    ELSE
      EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = vv_current_tenant()) WITH CHECK (tenant_id = vv_current_tenant())', t);
    END IF;
  END LOOP;
END $$;

-- ---------------------------------------------------------------- runtime roles and grants
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vv_app') THEN CREATE ROLE vv_app NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vv_worker') THEN CREATE ROLE vv_worker NOLOGIN; END IF;
END $$;

GRANT USAGE ON SCHEMA public TO vv_app, vv_worker;
GRANT SELECT ON tenants TO vv_app, vv_worker;
GRANT SELECT, INSERT, UPDATE ON memberships, console_sessions, api_keys, idempotency_keys, policies, subjects,
  sessions, applicant_sessions, attempts, contact_challenges, webhook_endpoints, webhook_deliveries TO vv_app, vv_worker;
GRANT SELECT, INSERT ON notice_acknowledgements, checks, decisions, usage_events, outbox, audit_events TO vv_app, vv_worker;
GRANT UPDATE (dispatched_at) ON outbox TO vv_worker;
GRANT SELECT, INSERT, UPDATE ON provider_events, rate_limit_windows, dummy_provider_attempts, dummy_messages TO vv_app, vv_worker;
GRANT DELETE ON rate_limit_windows TO vv_app, vv_worker;

-- Queue scanning: the worker may list pending queue rows across tenants, then
-- performs all domain work under that row's tenant context.
CREATE POLICY worker_scan ON outbox FOR SELECT TO vv_worker USING (true);
CREATE POLICY worker_scan ON webhook_deliveries FOR SELECT TO vv_worker USING (true);
CREATE POLICY worker_scan ON sessions FOR SELECT TO vv_worker
  USING (state IN ('created','in_progress','action_required') AND expires_at < now());

-- ---------------------------------------------------------------- pre-tenant lookups (SECURITY DEFINER)
CREATE FUNCTION vv_lookup_api_key(p_prefix text)
RETURNS TABLE (tenant_id text, id text, secret_hash text, scopes text[], expires_at timestamptz,
               revoked_at timestamptz, tenant_status text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT k.tenant_id, k.id, k.secret_hash, k.scopes, k.expires_at, k.revoked_at, t.status
  FROM api_keys k JOIN tenants t ON t.id = k.tenant_id WHERE k.prefix = p_prefix
$$;

CREATE FUNCTION vv_lookup_console_session(p_token_hash text)
RETURNS TABLE (tenant_id text, id text, membership_id text, csrf_hash text, user_subject text, role text,
               membership_active boolean, revoked_at timestamptz, last_seen_at timestamptz,
               absolute_expires_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT s.tenant_id, s.id, s.membership_id, s.csrf_hash, m.user_subject, m.role, m.active,
         s.revoked_at, s.last_seen_at, s.absolute_expires_at
  FROM console_sessions s JOIN memberships m ON m.tenant_id = s.tenant_id AND m.id = s.membership_id
  WHERE s.token_hash = p_token_hash
$$;

CREATE FUNCTION vv_lookup_hosted_token(p_token_hash text)
RETURNS TABLE (tenant_id text, session_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT tenant_id, id FROM sessions WHERE hosted_token_hash = p_token_hash
$$;

CREATE FUNCTION vv_lookup_applicant_session(p_token_hash text)
RETURNS TABLE (tenant_id text, id text, session_id text, expires_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT tenant_id, id, session_id, expires_at FROM applicant_sessions WHERE token_hash = p_token_hash
$$;

CREATE FUNCTION vv_resolve_provider_reference(p_provider text, p_reference text)
RETURNS TABLE (tenant_id text, session_id text, attempt_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT tenant_id, session_id, id FROM attempts WHERE provider = p_provider AND provider_reference = p_reference
$$;

REVOKE ALL ON FUNCTION vv_lookup_api_key(text), vv_lookup_console_session(text), vv_lookup_hosted_token(text),
  vv_lookup_applicant_session(text), vv_resolve_provider_reference(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_lookup_api_key(text), vv_lookup_console_session(text), vv_lookup_hosted_token(text),
  vv_lookup_applicant_session(text), vv_resolve_provider_reference(text, text) TO vv_app, vv_worker;
