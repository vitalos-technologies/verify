-- Fixes from the second independent verification (D-A..D-I).
-- D-A/D-C: tombstones are exported to a log outside the database backup; export progress tracked here.
ALTER TABLE deletion_jobs ADD COLUMN exported_version integer NOT NULL DEFAULT 0;
-- D-D: appeal overrides need a second, different reviewer.
ALTER TABLE appeals DROP CONSTRAINT appeals_status_check;
ALTER TABLE appeals ADD CONSTRAINT appeals_status_check CHECK (status IN ('open','claimed','awaiting_second_review','resolved'));
ALTER TABLE appeals ADD COLUMN proposal jsonb;
ALTER TABLE appeals ADD COLUMN proposed_by text;
-- D-G/D-I: OIDC state bound to the starting browser; requested max_age recorded.
ALTER TABLE oidc_logins ADD COLUMN browser_binding_hash text;
ALTER TABLE oidc_logins ADD COLUMN max_age integer;
ALTER TABLE oidc_logins ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
