-- CreateEnum
CREATE TYPE "MenuItemType" AS ENUM ('LINK', 'BUTTON');

-- AlterTable
ALTER TABLE "menu_items" ADD COLUMN "type" "MenuItemType" NOT NULL DEFAULT 'LINK';
ALTER TABLE "menu_items" ADD COLUMN "button_style" TEXT;
ALTER TABLE "menu_items" ADD COLUMN "button_action" TEXT;
ALTER TABLE "menu_items" ADD COLUMN "external_url" TEXT;









