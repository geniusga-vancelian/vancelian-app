#!/usr/bin/env python3
"""
Post-process prisma-case-format output so Prisma client delegates match Next.js usage
(prisma.page, prisma.investmentCategory, relation field `page`, `section`, etc.).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "prisma" / "schema.prisma"


def main() -> None:
    text = SCHEMA.read_text()
    text = text.replace("LegacyJsonPages", "___LEGACY_JSON_PAGES___")

    # Longest-first renames of model/type identifiers (PascalCase)
    renames = [
        ("SectionContents", "SectionContent"),
        ("ArticleCategoryI18n", "ArticleCategoryI18n"),
        ("ArticleBlockI18n", "ArticleBlockI18n"),
        ("ArticleCategories", "ArticleCategory"),
        ("ArticleProjects", "ArticleProject"),
        ("ArticleBlocks", "ArticleBlock"),
        ("ArticleLinks", "ArticleLink"),
        ("ArticleI18n", "ArticleI18n"),
        ("Articles", "Article"),
        ("PortfolioProductConfigs", "PortfolioProductConfig"),
        ("ProjectMedias", "ProjectMedia"),
        ("MenuItemI18n", "MenuItemI18n"),
        ("MenuItems", "MenuItem"),
        ("InvestmentCategories", "InvestmentCategory"),
        ("HelpCollectionI18n", "HelpCollectionI18n"),
        ("HelpCollections", "HelpCollection"),
        ("HelpCategoryI18n", "HelpCategoryI18n"),
        ("HelpCategories", "HelpCategory"),
        ("HelpArticleBlocks", "HelpArticleBlock"),
        ("HelpArticleI18n", "HelpArticleI18n"),
        ("HelpArticles", "HelpArticle"),
        ("DsComponentChapters", "DsComponentChapter"),
        ("DsComponents", "DsComponent"),
        ("KeyInformationCategories", "KeyInformationCategory"),
        ("TranslationLogs", "TranslationLog"),
        ("Projects", "Project"),
        ("EmailTemplateEntities", "EmailTemplateEntity"),
        ("EmailModuleI18n", "EmailModuleI18n"),
        ("EmailModules", "EmailModule"),
        ("Pages", "Page"),
        ("Sections", "Section"),
        ("Menus", "Menu"),
        ("Sessions", "Session"),
        ("Users", "User"),
    ]
    for old, new in renames:
        text = text.replace(old, new)

    text = text.replace("___LEGACY_JSON_PAGES___", "LegacyJsonPages")

    # Singular FK relation field names (Prisma client property names)
    subs = [
        # MenuItem -> Page
        (r"(\n  )pages(\s+)(Page\?)\s+@relation", r"\1page\2\3         @relation"),
        (r"(\n  )pages(\s+)(Page)\s+@relation", r"\1page\2\3             @relation"),
        # Section -> Page
        (r"(\n  )pages(\s+)(Page)\s+@relation\(fields: \[pageId\]", r"\1page\2\3             @relation(fields: [pageId]"),
        # Session -> User
        (r"(\n  )users(\s+)(User)\s+@relation\(fields: \[userId\]", r"\1user\2\3             @relation(fields: [userId]"),
        # SectionContent -> Section / User (editor)
        (r"(\n  )sections(\s+)(Section)\s+@relation\(fields: \[sectionId\]", r"\1section\2\3           @relation(fields: [sectionId]"),
        (r"(\n  )users(\s+)(User\?)\s+@relation\(fields: \[updatedByUserId\]", r"\1updatedBy\2\3        @relation(fields: [updatedByUserId]"),
        # Media uploader
        (r"(\n  )users(\s+)(User\?)\s+@relation\(fields: \[uploadedByUserId\]", r"\1uploadedBy\2\3        @relation(fields: [uploadedByUserId]"),
        # MenuItem -> Menu
        (r"(\n  )menus(\s+)(Menu)\s+@relation\(fields: \[menuId\]", r"\1menu\2\3             @relation(fields: [menuId]"),
        # Article* -> Article
        (r"(\n  )articles(\s+)(Article)\s+@relation\(fields: \[articleId\]", r"\1article\2\3           @relation(fields: [articleId]"),
        # ArticleCategoryI18n -> ArticleCategory
        (
            r"(\n  )articleCategories(\s+)(ArticleCategory)\s+@relation\(fields: \[categoryId\]",
            r"\1articleCategory\2\3 @relation(fields: [categoryId]",
        ),
        # ArticleProject -> Project
        (r"(\n  )projects(\s+)(Project)\s+@relation\(fields: \[projectId\]", r"\1project\2\3           @relation(fields: [projectId]"),
        # Help* i18n parents
        (
            r"(\n  )helpCollections(\s+)(HelpCollection)\s+@relation",
            r"\1helpCollection\2\3 @relation",
        ),
        (
            r"(\n  )helpCategories(\s+)(HelpCategory)\s+@relation",
            r"\1helpCategory\2\3 @relation",
        ),
        (
            r"(\n  )helpArticles(\s+)(HelpArticle)\s+@relation\(fields: \[articleId\]",
            r"\1helpArticle\2\3    @relation(fields: [articleId]",
        ),
    ]
    for pat, repl in subs:
        text, n = re.subn(pat, repl, text)
        if n:
            pass  # optional: print(pat, n)

    SCHEMA.write_text(text)
    print(f"Wrote {SCHEMA}")


if __name__ == "__main__":
    main()
