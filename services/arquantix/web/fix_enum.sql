-- Add missing values to TranslationEntityType enum
ALTER TYPE "TranslationEntityType" ADD VALUE IF NOT EXISTS 'MENU_ITEM';
ALTER TYPE "TranslationEntityType" ADD VALUE IF NOT EXISTS 'ARTICLE_CATEGORY';
ALTER TYPE "TranslationEntityType" ADD VALUE IF NOT EXISTS 'MENU';









