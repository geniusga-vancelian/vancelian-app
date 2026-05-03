-- Optional illustration on FAQ Help Collections (admin + mobile list).

ALTER TABLE "help_collections" ADD COLUMN IF NOT EXISTS "cover_media_id" TEXT;

ALTER TABLE "help_collections"
  DROP CONSTRAINT IF EXISTS "help_collections_cover_media_id_fkey";

ALTER TABLE "help_collections"
  ADD CONSTRAINT "help_collections_cover_media_id_fkey"
  FOREIGN KEY ("cover_media_id") REFERENCES "media"("id")
  ON DELETE SET NULL ON UPDATE CASCADE;

CREATE INDEX IF NOT EXISTS "ix_help_collections_cover_media_id"
  ON "help_collections"("cover_media_id");
