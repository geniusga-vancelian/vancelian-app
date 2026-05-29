'use client'

import { buildArticleBlockElements, DocumentAttachmentRow } from '@/components/blog/ArticleBlockStream'
import { PortalArticleAuthorBlock } from '@/components/portal/academy/PortalArticleAuthorBlock'
import { PortalArticleHero } from '@/components/portal/academy/PortalArticleHero'
import { PortalArticleRelatedSection } from '@/components/portal/academy/PortalArticleRelatedSection'
import { PortalArticleSidebar } from '@/components/portal/academy/PortalArticleSidebar'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import type { PortalArticleView } from '@/lib/portal/portalArticleTypes'
import {
  resolveArticleHeroTags,
  resolveArticleSlug,
} from '@/lib/portal/portalArticleFormat'
import { portalAcademyHubRoute } from '@/lib/portal/portalArticleRouting'

type Props = {
  view: PortalArticleView
}

function resolveBlocks(view: PortalArticleView) {
  if (view.kind === 'editorial') return view.article.blocks
  return view.blocks
}

function resolveMeta(view: PortalArticleView) {
  if (view.kind === 'editorial') {
    const article = view.article
    return {
      title: article.i18n.title,
      standfirst: article.i18n.standfirst,
      authorName: article.authorName,
      authorRole: article.authorRole,
      coverUrl: article.coverUrl,
      publishedAt: article.publishedAt ? new Date(article.publishedAt) : new Date(article.createdAt),
      documents: article.documents,
      locale: article.locale,
    }
  }

  return {
    title: view.title,
    standfirst: view.standfirst,
    authorName: view.authorName,
    authorRole: null as string | null,
    coverUrl: view.coverUrl,
    publishedAt: view.publishedAt ? new Date(view.publishedAt) : new Date(view.createdAt),
    documents: view.documents,
    locale: view.locale,
  }
}

/** Détail article — handoff Article.html (`art-*` · `portal-placer-grid`). */
export function PortalArticleScreen({ view }: Props) {
  const blocks = resolveBlocks(view)
  const meta = resolveMeta(view)
  const { elements, headings } = buildArticleBlockElements(blocks)
  const readingTime = calculateReadingTime(blocks)
  const heroTags = resolveArticleHeroTags(view)
  const slug = resolveArticleSlug(view)

  const docs = Array.isArray(meta.documents)
    ? (meta.documents as { url?: string; title?: string }[]).filter((doc) => doc?.url)
    : []

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <div className="art-page">
            <PortalDetailBackLink href={portalAcademyHubRoute()} label="Back to Academy" />

            <PortalArticleHero
              title={meta.title}
              standfirst={meta.standfirst}
              authorName={meta.authorName}
              coverUrl={meta.coverUrl || null}
              publishedAt={meta.publishedAt}
              locale={meta.locale}
              readingTime={readingTime}
              categoryLabel={heroTags.categoryLabel}
              sectionLabel={heroTags.sectionLabel}
              categoryTone={heroTags.categoryTone}
            />

            <div className="art-prose">
              <div className="portal-article-body">
                {elements.map(({ blockId, element }) => (
                  <div key={blockId}>{element}</div>
                ))}

                {docs.length > 0 ? (
                  <div>
                    <h2 id="documents" className="art-prose__h2">
                      Documents
                    </h2>
                    <div className="space-y-3">
                      {docs.map((doc, index) => (
                        <DocumentAttachmentRow
                          key={`${doc.url}-${index}`}
                          url={doc.url!}
                          title={doc.title || 'Document'}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <PortalArticleAuthorBlock authorName={meta.authorName} authorRole={meta.authorRole} />

            <PortalArticleRelatedSection currentSlug={slug} />
          </div>
        }
        side={<PortalArticleSidebar title={meta.title} headings={headings} />}
      />
    </PortalPageContainer>
  )
}
