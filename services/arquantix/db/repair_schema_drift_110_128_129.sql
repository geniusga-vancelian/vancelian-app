-- Réparation conservatrice : aligner le DDL sur les migrations Alembic 110, 128, 129
-- lorsque alembic_version annonce déjà head mais que le schéma physique est incomplet.
--
-- AVANT toute exécution : backup complet (pg_dump -Fc), voir docs/arquantix/RUNBOOK.md.
--
-- Références code :
--   services/arquantix/api/alembic/versions/128_persons_login_frozen.py
--   services/arquantix/api/alembic/versions/129_persons_account_state.py
--   services/arquantix/api/alembic/versions/110_auth_passkeys_webauthn_challenges.py
--
-- Idempotent : safe à rejouer si une partie est déjà appliquée.

BEGIN;

-- --- 128 : persons.login_frozen ---
ALTER TABLE public.persons
  ADD COLUMN IF NOT EXISTS login_frozen boolean NOT NULL DEFAULT false;

-- --- 129 : persons.account_state + backfill (même logique que la migration) ---
ALTER TABLE public.persons
  ADD COLUMN IF NOT EXISTS account_state varchar(16);

UPDATE public.persons p
SET account_state = 'ACTIVE'
WHERE p.account_state IS NULL
  AND EXISTS (SELECT 1 FROM public.pe_clients c WHERE c.person_id = p.id)
  AND (p.profile_json->'security'->>'local_passcode_registered_at') IS NOT NULL;

-- Backfill PARTIAL : même logique qu’Alembic 129, uniquement si l’API a enrichi admin_users
-- (schéma Docker/CMS minimal sans person_id : requête ignorée, pas d’erreur).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'admin_users'
      AND column_name = 'person_id'
  ) THEN
    UPDATE public.persons p
    SET account_state = 'PARTIAL'
    WHERE p.account_state IS NULL
      AND EXISTS (
        SELECT 1 FROM public.admin_users u
        WHERE u.person_id = p.id
          AND u.mobile_app_allowed = true
          AND (
            u.email LIKE '%@signup.internal'
            OR (u.mobile_e164 IS NOT NULL AND trim(u.mobile_e164) <> '')
          )
      );
  END IF;
END $$;

-- --- 110 : auth_webauthn_challenges + auth_passkeys ---
CREATE TABLE IF NOT EXISTS public.auth_webauthn_challenges (
  id uuid NOT NULL,
  challenge_b64 varchar(512) NOT NULL,
  flow_type varchar(32) NOT NULL,
  user_id integer,
  identifier varchar(255),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT auth_webauthn_challenges_pkey PRIMARY KEY (id),
  CONSTRAINT auth_webauthn_challenges_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES public.admin_users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_webauthn_challenges_challenge_b64
  ON public.auth_webauthn_challenges (challenge_b64);

CREATE INDEX IF NOT EXISTS ix_auth_webauthn_challenges_expires_at
  ON public.auth_webauthn_challenges (expires_at);

CREATE TABLE IF NOT EXISTS public.auth_passkeys (
  id uuid NOT NULL,
  user_id integer NOT NULL,
  credential_id_b64 varchar(512) NOT NULL,
  public_key_b64 text NOT NULL,
  sign_count bigint NOT NULL DEFAULT 0,
  transports_json jsonb,
  device_label varchar(255),
  aaguid varchar(64),
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz,
  CONSTRAINT auth_passkeys_pkey PRIMARY KEY (id),
  CONSTRAINT auth_passkeys_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES public.admin_users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_auth_passkeys_user_id ON public.auth_passkeys (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_passkeys_credential_id_b64
  ON public.auth_passkeys (credential_id_b64);

COMMIT;
