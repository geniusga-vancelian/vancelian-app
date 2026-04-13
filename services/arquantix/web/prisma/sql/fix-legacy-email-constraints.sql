-- Drift Alembic 031 → PR4 (130) : la colonne email avait un UNIQUE implicite (pe_clients_email_key / admin_users_email_key).
-- La migration 130 remplace les index nommés ix_* par des index uniques partiels ; les anciennes contraintes peuvent rester
-- et font échouer `prisma db push` (DROP INDEX sur un index « possédé » par une contrainte UNIQUE).
ALTER TABLE public.pe_clients DROP CONSTRAINT IF EXISTS pe_clients_email_key;
ALTER TABLE public.admin_users DROP CONSTRAINT IF EXISTS admin_users_email_key;
