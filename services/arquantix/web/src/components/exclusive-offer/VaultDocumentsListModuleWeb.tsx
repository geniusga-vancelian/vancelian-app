'use client'

import { DocumentFolderIcon } from '@/components/design-system/extracted/atoms/document-folder-icon'
import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { cn } from '@/lib/utils'

export type VaultDocumentsListResolvedItem = {
  mediaId: string
  downloadUrl: string
  /** Nom affiché (fichier médiathèque) */
  displayName: string
  /** Libellé date (Europe/Paris, style YYYY-MM-DD HH:mm) */
  dateLabel: string
}

type Props = {
  /** Surtitre (pastille type | … |) — aligné module Steps (SectionFigmaBlockHeader). */
  subtitle?: string
  moduleTitle?: string
  description?: string
  items: VaultDocumentsListResolvedItem[]
}

/**
 * Liste de documents — en-tête aligné sur le module **Steps** (`SectionFigmaBlockHeader` : surtitre, titre module, description 18px noir).
 * Corps : zébrage blanc / gris (#F5F5F5), coins arrondis 10px par ligne, sans contour.
 */
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
    <div className="w-full bg-white px-0 py-6 md:py-8">
      {hasModuleHeader ? (
        <SectionFigmaBlockHeader
          className="!mb-8 md:!mb-10"
          eyebrow={sub || undefined}
          title={title || undefined}
          description={desc || undefined}
        />
      ) : null}

      <div>
        <ul className="flex flex-col gap-2">
          {items.map((item, index) => (
            <li key={`${item.mediaId}-${index}`}>
              <a
                href={item.downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                download
                className={cn(
                  'flex flex-col gap-3 rounded-[10px] px-5 py-4 md:grid md:grid-cols-[28px_minmax(0,1fr)_minmax(0,140px)] md:items-center md:gap-x-6 md:px-8 md:py-5',
                  index % 2 === 0 ? 'bg-white' : 'bg-[#F5F5F5]',
                )}
              >
                <div className="flex min-w-0 items-center gap-3 md:contents">
                  <DocumentFolderIcon className="text-[#62656E]" />
                  <span className="min-w-0 truncate font-['Avenir:Roman',sans-serif] text-base leading-snug text-black">
                    {item.displayName}
                  </span>
                </div>
                <span className="whitespace-nowrap pl-8 font-['Avenir:Roman',sans-serif] text-base leading-snug text-black md:pl-0 md:text-center">
                  {item.dateLabel}
                </span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
