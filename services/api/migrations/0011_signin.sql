-- Console sign-in (owner decision 10 Nov 2026): Google (OIDC) or email magic link as first factor,
-- then an authenticator app code (TOTP, RFC 6238) unless the IdP asserts MFA. Not tenant data.
CREATE TABLE magic_links (
  token_hash   text PRIMARY KEY,
  subject      text NOT NULL,                 -- email|<lower-case address>
  binding_hash text NOT NULL,                 -- browser that asked for the link
  tenant_hint  text,
  expires_at   timestamptz NOT NULL,
  used_at      timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE login_pending (
  token_hash   text PRIMARY KEY,
  subjects     text[] NOT NULL,               -- verified identities from the first factor
  first_factor text NOT NULL CHECK (first_factor IN ('google','oidc','email')),
  tenant_hint  text,
  failed       integer NOT NULL DEFAULT 0,
  expires_at   timestamptz NOT NULL,
  used_at      timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE user_mfa (
  subject       text PRIMARY KEY,             -- canonical subject (email|… when known)
  secret_sealed bytea NOT NULL,
  confirmed_at  timestamptz,
  last_step     bigint NOT NULL DEFAULT 0,    -- replay protection: a code is accepted once
  created_at    timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE ON magic_links, login_pending, user_mfa TO vv_app;
