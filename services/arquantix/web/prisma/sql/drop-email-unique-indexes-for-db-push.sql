-- Secours si un ancien schéma Prisma recréait `ix_*` sous le même nom qu’Alembic 130 (index unique partiel).
-- Schéma actuel : `uq_prisma_admin_users_email` / `uq_prisma_pe_clients_email` pour éviter ce conflit.
DROP INDEX IF EXISTS public.ix_admin_users_email;
DROP INDEX IF EXISTS public.ix_pe_clients_email;
