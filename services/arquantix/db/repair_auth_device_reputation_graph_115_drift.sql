-- Réparation conservatrice : graphe réputation device (Alembic 115) si absent après drift.
-- Crée auth_device_blacklist + tables du même flux (réputation, arêtes, findings).
--
-- AVANT exécution : backup (pg_dump -Fc), voir docs/arquantix/RUNBOOK.md.
--
-- Migration source :
--   services/arquantix/api/alembic/versions/115_auth_device_reputation_graph.py
--
-- Modèles SQLAlchemy :
--   services/arquantix/api/database.py — AuthDeviceReputation, AuthDeviceUsageEdge,
--   AuthDeviceBlacklist, AuthDeviceGraphFinding
--
-- Idempotent : CREATE IF NOT EXISTS uniquement ; pas de DROP de colonnes/tables.
-- FK session_id → auth_sessions : ajoutée seulement si public.auth_sessions existe.

BEGIN;

-- --- auth_device_reputation (PK device_hash) ---
CREATE TABLE IF NOT EXISTS public.auth_device_reputation (
  device_hash varchar(64) NOT NULL,
  global_risk_score integer NOT NULL DEFAULT 0,
  reputation_level varchar(16) NOT NULL DEFAULT 'LOW',
  total_sessions integer NOT NULL DEFAULT 0,
  unique_user_count integer NOT NULL DEFAULT 0,
  unique_ip_count integer NOT NULL DEFAULT 0,
  suspicious_event_count integer NOT NULL DEFAULT 0,
  blocked_until timestamptz NULL,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT auth_device_reputation_pkey PRIMARY KEY (device_hash)
);

-- --- auth_device_usage_edges (FK user_id toujours ; FK session_id conditionnelle) ---
CREATE TABLE IF NOT EXISTS public.auth_device_usage_edges (
  id uuid NOT NULL,
  device_hash varchar(64) NOT NULL,
  user_id integer NULL,
  session_id uuid NULL,
  ip_address varchar(45) NULL,
  event_type varchar(128) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT auth_device_usage_edges_pkey PRIMARY KEY (id),
  CONSTRAINT auth_device_usage_edges_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.admin_users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_auth_device_usage_edges_device_hash
  ON public.auth_device_usage_edges (device_hash);

CREATE INDEX IF NOT EXISTS ix_auth_device_usage_edges_user_id
  ON public.auth_device_usage_edges (user_id);

CREATE INDEX IF NOT EXISTS ix_auth_device_usage_edges_created_at
  ON public.auth_device_usage_edges (created_at);

DO $$
BEGIN
  IF to_regclass('public.auth_sessions') IS NOT NULL
     AND NOT EXISTS (
       SELECT 1 FROM pg_constraint
       WHERE conname = 'auth_device_usage_edges_session_id_fkey'
     ) THEN
    ALTER TABLE public.auth_device_usage_edges
      ADD CONSTRAINT auth_device_usage_edges_session_id_fkey
      FOREIGN KEY (session_id) REFERENCES public.auth_sessions (id) ON DELETE SET NULL;
  END IF;
END $$;

-- --- auth_device_blacklist ---
CREATE TABLE IF NOT EXISTS public.auth_device_blacklist (
  id uuid NOT NULL,
  device_hash varchar(64) NOT NULL,
  reason varchar(512) NOT NULL,
  blocked_until timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by integer NULL,
  CONSTRAINT auth_device_blacklist_pkey PRIMARY KEY (id),
  CONSTRAINT auth_device_blacklist_created_by_fkey
    FOREIGN KEY (created_by) REFERENCES public.admin_users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_auth_device_blacklist_device_hash
  ON public.auth_device_blacklist (device_hash);

-- --- auth_device_graph_findings ---
CREATE TABLE IF NOT EXISTS public.auth_device_graph_findings (
  id uuid NOT NULL,
  device_hash varchar(64) NULL,
  user_id integer NULL,
  finding_type varchar(128) NOT NULL,
  severity varchar(16) NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT auth_device_graph_findings_pkey PRIMARY KEY (id),
  CONSTRAINT auth_device_graph_findings_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES public.admin_users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_auth_device_graph_findings_device_hash
  ON public.auth_device_graph_findings (device_hash);

CREATE INDEX IF NOT EXISTS ix_auth_device_graph_findings_created_at
  ON public.auth_device_graph_findings (created_at);

COMMIT;
