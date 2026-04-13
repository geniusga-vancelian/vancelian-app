ALTER TABLE "articles" ADD COLUMN "is_milestone" BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX "articles_is_milestone_idx" ON "articles"("is_milestone");
