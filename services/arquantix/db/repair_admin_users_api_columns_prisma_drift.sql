-- Réparation conservatrice : réintroduire les colonnes API-only sur public.admin_users
-- supprimées par un `prisma db push` alors que SQLAlchemy (services/arquantix/api/database.py)
-- et les migrations Alembic les attendent encore.
--
-- AVANT exécution : backup (pg_dump -Fc), voir docs/arquantix/RUNBOOK.md.
--
-- Références Alembic :
--   114_tier1_global_risk_security_response.py  → security_* columns
--   116_zero_trust_security_decisions.py         → zero_trust_role
--   117_admin_mobile_login_otp.py                → mobile_e164 + index partiel
--   120_admin_users_person_id.py                 → person_id + FK + index unique
--   127_admin_users_mobile_app_allowed.py        → mobile_app_allowed
--
-- Idempotent : safe à rejouer.

BEGIN;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS security_account_locked_until timestamptz NULL;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS security_flagged boolean NOT NULL DEFAULT false;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS security_refresh_blocked boolean NOT NULL DEFAULT false;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS zero_trust_role varchar(32) NOT NULL DEFAULT 'admin';

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS mobile_e164 varchar(24) NULL;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS person_id uuid NULL;

ALTER TABLE public.admin_users
  ADD COLUMN IF NOT EXISTS mobile_app_allowed boolean NOT NULL DEFAULT true;

-- Index partiel identique Alembic 117 (unicité E.164 non nul).
CREATE UNIQUE INDEX IF NOT EXISTS uq_admin_users_mobile_e164
  ON public.admin_users (mobile_e164)
  WHERE (mobile_e164 IS NOT NULL);

-- Index unique 1:1 optionnel person_id (Alembic 120).
CREATE UNIQUE INDEX IF NOT EXISTS ix_admin_users_person_id
  ON public.admin_users (person_id);

-- FK vers persons (Alembic 120) — seulement si la table cible existe et la contrainte absente.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'persons'
  ) AND NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_admin_users_person_id_persons'
  ) THEN
    ALTER TABLE public.admin_users
      ADD CONSTRAINT fk_admin_users_person_id_persons
      FOREIGN KEY (person_id) REFERENCES public.persons (id) ON DELETE SET NULL;
  END IF;
END $$;

COMMIT;
