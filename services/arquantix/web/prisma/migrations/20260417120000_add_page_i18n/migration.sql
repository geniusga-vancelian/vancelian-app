-- Phase 2A — metadata localisées par page (SEO i18n)
CREATE TABLE "page_i18n" (
    "id" TEXT NOT NULL,
    "page_id" TEXT NOT NULL,
    "locale" VARCHAR(5) NOT NULL,
    "title" TEXT,
    "description" TEXT,
    "og_title" TEXT,
    "og_description" TEXT,

    CONSTRAINT "page_i18n_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "page_i18n_page_id_locale_key" ON "page_i18n"("page_id", "locale");

ALTER TABLE "page_i18n" ADD CONSTRAINT "page_i18n_page_id_fkey" FOREIGN KEY ("page_id") REFERENCES "pages"("id") ON DELETE CASCADE ON UPDATE CASCADE;
