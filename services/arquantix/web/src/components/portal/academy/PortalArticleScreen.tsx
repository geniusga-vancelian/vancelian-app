'use client'

import { buildArticleBlockElements, DocumentAttachmentRow } from '@/components/blog/ArticleBlockStream'
import { TableOfContents } from '@/components/blog/TableOfContents'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import type { PortalArticleView } from '@/lib/portal/portalArticleTypes'
import { portalArticleTypeLabel } from '@/lib/portal/portalArticleTypes'
import { portalAcademyHubRoute } from '@/lib/portal/portalArticleRouting'
import { cn } from '@/lib/utils'

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
      createdAt: new Date(article.createdAt),
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
    createdAt: new Date(view.createdAt),
    documents: view.documents,
    locale: view.locale,
  }
}

export function PortalArticleScreen({ view }: Props) {
  const blocks = resolveBlocks(view)
  const meta = resolveMeta(view)
  const { elements, headings } = buildArticleBlockElements(blocks)
  const readingTime = calculateReadingTime(blocks)
  const typeLabel = portalArticleTypeLabel(view)
  const docs = Array.isArray(meta.documents)
    ? (meta.documents as { url?: string; title?: string }[]).filter((doc) => doc?.url)
    : []

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <nav className="mb-2 font-ui text-[12px] text-v-fg-muted" aria-label="Fil d'Ariane">
            <ol className="m-0 flex list-none flex-wrap items-center gap-x-2 gap-y-1 p-0">
              <li>
                <PortalNavLink
                  href={portalAcademyHubRoute()}
                  className="text-v-fg-muted no-underline transition-colors hover:text-v-fg"
                >
                  Academy
                </PortalNavLink>
              </li>
              <li aria-hidden className="text-v-fg-20">
                ›
              </li>
              <li className="line-clamp-1 text-v-fg-body">{meta.title}</li>
            </ol>
          </nav>
        </PortalReveal>

        <PortalReveal index={1}>
          <article className="flex flex-col gap-6">
            <header className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <AppEyebrow>{typeLabel}</AppEyebrow>
                {view.kind === 'academy' ? (
                  <span className="rounded-v-tag border border-v-fg-10 px-2 py-0.5 font-ui text-[11px] font-medium text-v-fg-muted">
                    {view.categoryTitle}
                  </span>
                ) : null}
              </div>
              <h1 className="m-0 font-ui text-[28px] font-semibold leading-tight tracking-v-tight text-v-fg">
                {meta.title}
              </h1>
              {meta.standfirst ? (
                <p className="m-0 max-w-2xl font-ui text-[15px] leading-relaxed text-v-fg-body">
                  {meta.standfirst}
                </p>
              ) : null}
              <p className="m-0 font-ui text-[13px] text-v-fg-muted">
                <span className="font-medium text-v-fg">{meta.authorName}</span>
                {meta.authorRole ? ` · ${meta.authorRole}` : null}
                {' · '}
                {formatArticleDateShort(meta.createdAt, meta.locale)}
                {' · '}
                {readingTime} min
              </p>
            </header>

            {meta.coverUrl ? (
              <div className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-fg-05">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={meta.coverUrl} alt="" className="aspect-[3/2] w-full object-cover" />
              </div>
            ) : null}

            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10">
              {headings.length >= 3 ? (
                <aside className="hidden lg:block">
                  <TableOfContents
                    headings={headings}
                    title="In this article"
                    minCount={3}
                    navClassName="w-full"
                  />
                </aside>
              ) : null}

              <div
                className={cn(
                  'portal-article-body min-w-0',
                  headings.length < 3 && 'lg:col-span-2',
                )}
              >
                {elements.map(({ blockId, element }) => (
                  <div key={blockId}>{element}</div>
                ))}

                {docs.length > 0 ? (
                  <div className="mt-10 border-t border-v-fg-10 pt-6">
                    <h2 className="m-0 mb-3 font-ui text-[16px] font-semibold text-v-fg">
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
          </article>
        </PortalReveal>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
