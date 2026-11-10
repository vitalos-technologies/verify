-- Platform administration and operations consoles (04_user_experience §Surface inventory: Operations, Superadmin).
-- Platform staff see metadata only: no subject references, contact data or evidence (10_review §Support access).
CREATE TABLE platform_operators (
  id          text PRIMARY KEY,
  subject     text NOT NULL UNIQUE,
  display_name text NOT NULL,
  role        text NOT NULL CHECK (role IN ('platform_admin','operations')),
  active      boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE platform_sessions (
  id           text PRIMARY KEY,
  operator_id  text NOT NULL REFERENCES platform_operators(id),
  token_hash   text NOT NULL UNIQUE,
  csrf_hash    text NOT NULL,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  absolute_expires_at timestamptz NOT NULL,
  revoked_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE ON platform_operators, platform_sessions TO vv_app;

CREATE FUNCTION vv_platform_organisations()
RETURNS TABLE (id text, name text, status text, region_policy text[], monthly_session_cap integer,
               month_sessions bigint, month_completed bigint, published_policies bigint, required_checks text[],
               members bigint, created_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT t.id, t.name, t.status, t.region_policy, t.monthly_session_cap,
    (SELECT count(*) FROM sessions s WHERE s.tenant_id = t.id AND s.created_at >= date_trunc('month', now())),
    (SELECT count(*) FROM usage_events u WHERE u.tenant_id = t.id AND u.charge_type = 'completed_verification'
       AND u.created_at >= date_trunc('month', now())),
    (SELECT count(*) FROM policies p WHERE p.tenant_id = t.id AND p.status = 'published'),
    (SELECT array_agg(DISTINCT c) FROM policies p, jsonb_array_elements_text(p.definition->'required_checks') c
       WHERE p.tenant_id = t.id AND p.status = 'published'),
    (SELECT count(*) FROM memberships m WHERE m.tenant_id = t.id AND m.active),
    t.created_at
  FROM tenants t ORDER BY t.created_at
$$;

CREATE FUNCTION vv_platform_tenant_activity(p_tenant text, p_limit integer)
RETURNS TABLE (action text, actor_type text, created_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT action, actor_type, created_at FROM audit_events
  WHERE tenant_id = p_tenant AND action IN ('policy.publish','api_key.create','api_key.revoke','membership.revoke',
    'webhook.create','billing.invoice','billing.credit','legal_hold.place','console.sign_in')
  ORDER BY created_at DESC LIMIT least(p_limit, 50)
$$;

CREATE FUNCTION vv_platform_queues()
RETURNS TABLE (queue text, pending bigint, oldest timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT 'identity_checks', count(*), min(updated_at) FROM sessions WHERE state = 'processing'
  UNION ALL SELECT 'provider_callbacks', count(*), min(received_at) FROM provider_events
    WHERE processing_state IN ('pending','retry','processing')
  UNION ALL SELECT 'customer_webhooks', count(*), min(created_at) FROM webhook_deliveries WHERE state = 'pending'
  UNION ALL SELECT 'evidence_deletion', count(*), min(created_at) FROM deletion_jobs WHERE state NOT IN ('complete')
$$;

CREATE FUNCTION vv_platform_provider_health(p_days integer)
RETURNS TABLE (provider text, day date, total bigint, failed bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT provider, received_at::date, count(*),
         count(*) FILTER (WHERE processing_state IN ('failed') OR (processing_state = 'retry' AND attempts > 1))
  FROM provider_events WHERE received_at >= now() - make_interval(days => p_days)
  GROUP BY 1, 2 ORDER BY 1, 2
$$;

CREATE FUNCTION vv_platform_counters()
RETURNS TABLE (deletions_due_today bigint, failed_webhooks bigint, quarantined_events bigint, error_sessions bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT (SELECT count(*) FROM deletion_jobs WHERE state = 'awaiting_backup_expiry'
            AND backup_expires_at < now() + interval '1 day'),
         (SELECT count(*) FROM webhook_deliveries WHERE state IN ('failed','blocked')),
         (SELECT count(*) FROM provider_events WHERE processing_state = 'quarantined'),
         (SELECT count(*) FROM sessions WHERE state = 'error')
$$;

REVOKE ALL ON FUNCTION vv_platform_organisations(), vv_platform_tenant_activity(text, integer), vv_platform_queues(),
  vv_platform_provider_health(integer), vv_platform_counters() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vv_platform_organisations(), vv_platform_tenant_activity(text, integer), vv_platform_queues(),
  vv_platform_provider_health(integer), vv_platform_counters() TO vv_app;
