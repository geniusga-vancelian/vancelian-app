-- CreateTable
CREATE TABLE "menus" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "menus_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "menu_items" (
    "id" TEXT NOT NULL,
    "menu_id" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "slug" TEXT,
    "is_home" BOOLEAN NOT NULL DEFAULT false,
    "url_path" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "enabled" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "menu_items_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "menus_key_key" ON "menus"("key");

-- CreateIndex
CREATE INDEX "menu_items_menu_id_idx" ON "menu_items"("menu_id");

-- CreateIndex
CREATE UNIQUE INDEX "menu_items_menu_id_order_key" ON "menu_items"("menu_id", "order");

-- AddForeignKey
ALTER TABLE "menu_items" ADD CONSTRAINT "menu_items_menu_id_fkey" FOREIGN KEY ("menu_id") REFERENCES "menus"("id") ON DELETE CASCADE ON UPDATE CASCADE;
