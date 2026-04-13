-- PR4: admin_users.email nullable (alignement schéma CMS / index unique partiel).
-- Idempotent si la colonne est déjà nullable.

ALTER TABLE "admin_users" ALTER COLUMN "email" DROP NOT NULL;
