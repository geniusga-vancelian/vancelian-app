-- CreateEnum
CREATE TYPE "MenuNavigationNodeKind" AS ENUM ('PAGE', 'GROUP', 'EXTERNAL_LINK');

-- AlterTable
ALTER TABLE "menu_items" ADD COLUMN "navigation_node_kind" "MenuNavigationNodeKind" NOT NULL DEFAULT 'PAGE';
ALTER TABLE "menu_items" ADD COLUMN "open_in_new_tab" BOOLEAN NOT NULL DEFAULT false;

-- AlterTable
ALTER TABLE "pages" ADD COLUMN "show_in_mega_menu" BOOLEAN NOT NULL DEFAULT true;
