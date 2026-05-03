-- Lot 1 : hiérarchie Page (additive) + backfill prudent.

-- CreateEnum
CREATE TYPE "PageRole" AS ENUM ('STANDARD', 'HOME', 'PROJECTS_HUB');

-- AlterTable
ALTER TABLE "pages" ADD COLUMN "parent_id" TEXT,
ADD COLUMN "sort_order" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN "page_role" "PageRole" NOT NULL DEFAULT 'STANDARD',
ADD COLUMN "show_in_nav" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN "is_system_page" BOOLEAN NOT NULL DEFAULT false;

-- AddForeignKey
ALTER TABLE "pages" ADD CONSTRAINT "pages_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "pages"("id") ON DELETE SET NULL ON UPDATE CASCADE;

CREATE INDEX "ix_pages_parent_id" ON "pages"("parent_id");
CREATE INDEX "ix_pages_parent_sort" ON "pages"("parent_id", "sort_order");

-- Backfill : home = rôle HOME + système
UPDATE "pages"
SET "page_role" = 'HOME',
    "is_system_page" = true
WHERE "slug" = 'home';

-- Hub projets : uniquement par slug stable `projects` (page CMS liste / hub)
UPDATE "pages"
SET "page_role" = 'PROJECTS_HUB'
WHERE "slug" = 'projects';

-- Rattachement déterministe des vaults sous le hub `projects` si la page existe.
-- Exclut `home` et le slug `projects` lui-même ; n’agit que sur template vault_builder.
UPDATE "pages" AS p
SET "parent_id" = hub."id"
FROM (SELECT "id" FROM "pages" WHERE "slug" = 'projects' LIMIT 1) AS hub
WHERE p."template" = 'vault_builder'
  AND p."slug" NOT IN ('home', 'projects')
  AND p."id" <> hub."id";

-- Ordre des vaults rattachés : stable par date de création
WITH hub AS (
  SELECT "id" FROM "pages" WHERE "slug" = 'projects' LIMIT 1
),
vaults AS (
  SELECT p."id",
         (ROW_NUMBER() OVER (ORDER BY p."created_at" ASC) - 1) AS rn
  FROM "pages" AS p,
       hub
  WHERE p."parent_id" = hub."id"
    AND p."template" = 'vault_builder'
)
UPDATE "pages" AS p
SET "sort_order" = v.rn
FROM vaults AS v
WHERE p."id" = v."id";
