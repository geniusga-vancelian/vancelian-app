-- Lien canonique CMS (users) → API Python (admin_users) pour le BFF JWT (PR3.1).
-- Backfill : aligner les comptes déjà présents par email (une fois, hors chemin runtime JWT).

ALTER TABLE "users" ADD COLUMN "admin_user_id" INTEGER;

CREATE UNIQUE INDEX "users_admin_user_id_key" ON "users"("admin_user_id");

ALTER TABLE "users" ADD CONSTRAINT "users_admin_user_id_fkey" FOREIGN KEY ("admin_user_id") REFERENCES "admin_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

UPDATE "users" AS u
SET "admin_user_id" = au."id"
FROM "admin_users" AS au
WHERE u."email" = au."email"
  AND u."admin_user_id" IS NULL;
