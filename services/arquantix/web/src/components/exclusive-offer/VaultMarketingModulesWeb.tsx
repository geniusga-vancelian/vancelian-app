'use client'

import Link from 'next/link'
import { VaultModuleHeader } from '@/components/exclusive-offer/VaultModuleHeader'
import {
  VAULT_MODULE_CARD_CLASS,
  VAULT_MODULE_IMAGE_CLASS,
} from '@/components/design-system/vaultTokens'
import { cn } from '@/lib/utils'

type CardItem = {
  imageUrl: string
  title: string
  description: string
  href: string
}

function readCardItems(raw: unknown): CardItem[] {
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    if (it == null || typeof it !== 'object' || Array.isArray(it)) return []
    const row = it as Record<string, unknown>
    const imageUrl =
      typeof row.imageUrl === 'string'
        ? row.imageUrl
        : typeof row.posterImageUrl === 'string'
          ? row.posterImageUrl
          : ''
    const title = typeof row.title === 'string' ? row.title.trim() : ''
    const description = typeof row.description === 'string' ? row.description.trim() : ''
    const href =
      typeof row.redirectUrl === 'string'
        ? row.redirectUrl
        : typeof row.href === 'string'
          ? row.href
          : ''
    if (!imageUrl.trim()) return []
    return [{ imageUrl: imageUrl.trim(), title, description, href: href.trim() }]
  })
}

function MarketingCard({ item, portrait }: { item: CardItem; portrait?: boolean }) {
  const body = (
    <article className={cn(VAULT_MODULE_CARD_CLASS, 'overflow-hidden p-0')}>
      <div className={cn(VAULT_MODULE_IMAGE_CLASS, portrait ? 'aspect-[3/4]' : 'aspect-[16/10]')}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={item.imageUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
      </div>
      {item.title || item.description ? (
        <div className="space-y-2 p-5">
          {item.title ? (
            <h3 className="m-0 font-ui text-[18px] font-semibold leading-snug text-v-fg">
              {item.title}
            </h3>
          ) : null}
          {item.description ? (
            <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              {item.description}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  )

  if (item.href) {
    return (
      <Link href={item.href} className="block no-underline transition-opacity hover:opacity-95">
        {body}
      </Link>
    )
  }
  return body
}

export function VaultMarketingLargePortraitWeb({ content }: { content: Record<string, unknown> }) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const imageUrl =
    typeof content.imageUrl === 'string'
      ? content.imageUrl
      : typeof content.imageAssetPath === 'string'
        ? content.imageAssetPath
        : ''
  if (!imageUrl.trim() && !title) return null

  return (
    <div className="w-full space-y-6">
      <VaultModuleHeader title={title || undefined} />
      {imageUrl.trim() ? (
        <div className={cn(VAULT_MODULE_IMAGE_CLASS, 'mx-auto aspect-[3/4] max-w-md')}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl.trim()} alt="" className="h-full w-full object-cover" loading="lazy" />
        </div>
      ) : null}
    </div>
  )
}

export function VaultMarketingCardsCarouselWeb({
  content,
  portrait,
}: {
  content: Record<string, unknown>
  portrait?: boolean
}) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const items = readCardItems(content.items)
  if (!items.length && !title) return null

  return (
    <div className="w-full space-y-6">
      <VaultModuleHeader title={title || undefined} />
      <div
        className={cn(
          'grid gap-4',
          portrait ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 md:grid-cols-2',
        )}
      >
        {items.map((item, i) => (
          <MarketingCard key={`${item.imageUrl}-${i}`} item={item} portrait={portrait} />
        ))}
      </div>
    </div>
  )
}
