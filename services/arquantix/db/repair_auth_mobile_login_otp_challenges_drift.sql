-- Réparation conservatrice : créer public.auth_mobile_login_otp_challenges si absente
-- (dérive après outil hors Alembic, ex. schéma incomplet / table jamais migrée).
--
-- AVANT exécution : backup (pg_dump -Fc), voir docs/arquantix/RUNBOOK.md.
--
-- Migration source Alembic :
--   services/arquantix/api/alembic/versions/117_admin_mobile_login_otp.py
--
-- Modèle SQLAlchemy :
--   services/arquantix/api/database.py — class AuthMobileLoginOtpChallenge
--
-- Idempotent : ne supprime rien ; safe à rejouer.

BEGIN;

CREATE TABLE IF NOT EXISTS public.auth_mobile_login_otp_challenges (
  id uuid NOT NULL,
  phone_e164_normalized varchar(24) NOT NULL,
  code_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  attempt_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT auth_mobile_login_otp_challenges_pkey PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_mobile_login_otp_phone
  ON public.auth_mobile_login_otp_challenges (phone_e164_normalized);

CREATE INDEX IF NOT EXISTS ix_auth_mobile_login_otp_expires_at
  ON public.auth_mobile_login_otp_challenges (expires_at);

COMMIT;
