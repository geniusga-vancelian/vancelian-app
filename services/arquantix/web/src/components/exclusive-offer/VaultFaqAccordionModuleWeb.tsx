'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import FAQ from '@/components/design-system/FAQ'
import {
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
} from '@/lib/i18n/publicLocalizedRouting'
import { VAULT_MODULE_CARD_CLASS, VAULT_MODULE_LINK_CLASS } from '@/components/design-system/vaultTokens'
import { ArticleBodyMarkdown } from '@/lib/blog/articleBodyMarkdown'

type Props = {
  content: Record<string, unknown>
}

function readFaqItems(content: Record<string, unknown>) {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    if (it == null || typeof it !== 'object' || Array.isArray(it)) return []
    const row = it as Record<string, unknown>
    const question = typeof row.question === 'string' ? row.question.trim() : ''
    const answer =
      typeof row.standfirst === 'string'
        ? row.standfirst.trim()
        : typeof row.answer === 'string'
          ? row.answer.trim()
          : ''
    if (!question || !answer) return []
    return [{ question, answer }]
  })
}

export function VaultFaqAccordionModuleWeb({ content }: Props) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const titleRaw = typeof content.title === 'string' ? content.title.trim() : ''
  const introRaw = typeof content.intro === 'string' ? content.intro.trim() : ''
  const footerLabel = typeof content.footerLinkLabel === 'string' ? content.footerLinkLabel.trim() : ''
  const footerLinkUrlRaw = typeof content.footerLinkUrl === 'string' ? content.footerLinkUrl.trim() : ''
  const coll = typeof content.footerCollectionSlug === 'string' ? content.footerCollectionSlug.trim() : ''
  const cat = typeof content.footerCategorySlug === 'string' ? content.footerCategorySlug.trim() : ''
  const fromSlugs = coll && cat ? `/help/${coll}/${cat}` : coll ? `/help/${coll}` : ''

  const items = readFaqItems(content)
  if (!titleRaw && !introRaw && items.length === 0 && !footerLabel) {
    return null
  }

  let footerHref: string | null = null
  if (footerLabel) {
    if (footerLinkUrlRaw) {
      footerHref = /^https?:\/\//i.test(footerLinkUrlRaw)
        ? footerLinkUrlRaw
        : localizePublicInternalHref(
            footerLinkUrlRaw.startsWith('/') ? footerLinkUrlRaw : `/${footerLinkUrlRaw}`,
            loc,
          )
    } else if (fromSlugs) {
      footerHref = localizePublicInternalHref(fromSlugs, loc)
    }
  }

  return (
    <div className={VAULT_MODULE_CARD_CLASS}>
      {items.length > 0 ? (
        <FAQ
          items={items}
          headline={titleRaw || undefined}
          description={introRaw || undefined}
        />
      ) : (
        <div className="space-y-3 text-center">
          {titleRaw ? (
            <h2 className="font-ui text-[clamp(28px,3vw,40px)] font-semibold leading-[1.1] text-v-fg">
              {titleRaw}
            </h2>
          ) : null}
          {introRaw ? (
            <p className="font-ui text-[18px] leading-relaxed text-v-fg-body">
              <ArticleBodyMarkdown text={introRaw} variant="inline" />
            </p>
          ) : null}
        </div>
      )}
      {footerLabel && footerHref ? (
        <div className="mt-6 flex justify-center">
          <Link href={footerHref} className={VAULT_MODULE_LINK_CLASS}>
            {footerLabel}
          </Link>
        </div>
      ) : null}
    </div>
  )
}
