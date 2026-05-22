'use client'

import { DocumentFolderIcon } from '@/components/design-system/extracted/atoms/document-folder-icon'
import { VaultModuleHeader } from '@/components/exclusive-offer/VaultModuleHeader'
import { vaultStripeClass } from '@/components/design-system/vaultTokens'
import { cn } from '@/lib/utils'

export type VaultDocumentsListResolvedItem = {
  mediaId: string
  downloadUrl: string
  displayName: string
  dateLabel: string
}

type Props = {
  subtitle?: string
  moduleTitle?: string
  description?: string
  items: VaultDocumentsListResolvedItem[]
}

export function VaultDocumentsListModuleWeb({
  subtitle,
  moduleTitle,
  description,
  items,
}: Props) {
  if (!items.length) return null

  const sub = subtitle?.trim() ?? ''
  const title = moduleTitle?.trim() ?? ''
  const desc = description?.trim() ?? ''
  const hasModuleHeader = Boolean(sub || title || desc)

  return (
    <div className="w-full px-0 py-6 md:py-8">
      {hasModuleHeader ? (
        <VaultModuleHeader eyebrow={sub || undefined} title={title || undefined} description={desc || undefined} />
      ) : null}

      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {items.map((item, index) => (
          <li key={`${item.mediaId}-${index}`}>
            <a
              href={item.downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              download
              className={cn(
                'flex flex-col gap-3 rounded-v-card px-5 py-4 md:grid md:grid-cols-[28px_minmax(0,1fr)_minmax(0,140px)] md:items-center md:gap-x-6 md:px-8 md:py-5',
                vaultStripeClass(index),
              )}
            >
              <div className="flex min-w-0 items-center gap-3 md:contents">
                <DocumentFolderIcon className="text-v-fg-muted" />
                <span className="min-w-0 truncate font-ui text-[15px] leading-snug text-v-fg md:text-base">
                  {item.displayName}
                </span>
              </div>
              <span className="whitespace-nowrap pl-8 font-ui text-[14px] leading-snug text-v-fg-body md:pl-0 md:text-center md:text-base">
                {item.dateLabel}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
