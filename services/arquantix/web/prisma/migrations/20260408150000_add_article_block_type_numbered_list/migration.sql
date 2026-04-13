-- Align PostgreSQL enum with Prisma `ArticleBlockType` (NUMBERED_LIST).
ALTER TYPE "ArticleBlockType" ADD VALUE IF NOT EXISTS 'NUMBERED_LIST';
