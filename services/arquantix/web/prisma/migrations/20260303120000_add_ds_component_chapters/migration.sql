-- CreateTable
CREATE TABLE "ds_component_chapters" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ds_component_chapters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ds_components" (
    "id" TEXT NOT NULL,
    "chapter_id" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "schema_json" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ds_components_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ds_component_chapters_slug_key" ON "ds_component_chapters"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "ds_components_chapter_id_slug_key" ON "ds_components"("chapter_id", "slug");

-- CreateIndex
CREATE INDEX "ds_components_chapter_id_idx" ON "ds_components"("chapter_id");

-- AddForeignKey
ALTER TABLE "ds_components" ADD CONSTRAINT "ds_components_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "ds_component_chapters"("id") ON DELETE CASCADE ON UPDATE CASCADE;
