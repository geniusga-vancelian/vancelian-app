'use client'

import { useLayoutEffect, useRef, useState } from 'react'

import {
  SIMPLE_MARKDOWN_MODULE_TITLE_TYPO,
  VAULT_MODULE_DESCRIPTION_TYPO,
  VAULT_MODULE_IMAGE_CLASS,
} from '@/components/design-system'
import { cn } from '@/lib/utils'

/** Doit rester aligné sur `gap-2` (8px) entre les 2 colonnes de la 1ʳᵉ ligne 50/50. */
const DESKTOP_COL_GAP_PX = 8

export type VaultCarouselResolvedItem = {
  url: string
  alt: string | null
  mediaId: string
}

type Props = {
  moduleTitle?: string
  description?: string
  items: VaultCarouselResolvedItem[]
}

/** md (≥768px) : 2 images / rangée avec motif 50/50 · 60/40 · 40/60 répété ; en dessous : pile 1 image / ligne. */
const MD_BREAKPOINT = 'md'

function CarouselImage({
  item,
  priority,
}: {
  item: VaultCarouselResolvedItem
  priority: boolean
}) {
  return (
    <div className={cn(VAULT_MODULE_IMAGE_CLASS, 'relative aspect-[16/10] w-full')}>
      {/* eslint-disable-next-line @next/next/no-img-element -- URLs présignées / externes */}
      <img
        src={item.url}
        alt={item.alt?.trim() || ''}
        className="h-full w-full object-cover"
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
      />
    </div>
  )
}

/**
 * Une seule image : même principe que le bloc **Image** des articles (pleine largeur, hauteur
 * naturelle, `rounded-[14px]`) — cohérent avec le rendu « image pleine page » côté offre exclusive.
 */
function SingleImageLayout({ item }: { item: VaultCarouselResolvedItem }) {
  return (
    <figure className="w-full">
      <div className={cn(VAULT_MODULE_IMAGE_CLASS, 'overflow-hidden rounded-v-card')}>
        {/* eslint-disable-next-line @next/next/no-img-element -- URLs présignées / externes */}
        <img
          src={item.url}
          alt={item.alt?.trim() || ''}
          className="h-auto w-full object-cover"
          loading="eager"
          decoding="async"
        />
      </div>
    </figure>
  )
}

/**
 * Deux images côte à côte : hauteur de rangée = `rowHeight` (carré 50/50 de la 1ʳᵉ ligne :
 * côté d’un carré = (largeur conteneur − gap) / 2). Toutes les lignes desktop réutilisent
 * cette hauteur (60/40 et 40/60 compris) ; `object-cover` pour remplir sans déformation.
 */
function PairedRowTwoImages({
  left,
  right,
  colTemplate,
  priorityLeft,
  priorityRight,
  rowHeight,
}: {
  left: VaultCarouselResolvedItem
  right: VaultCarouselResolvedItem
  colTemplate: '50-50' | '60-40' | '40-60'
  priorityLeft: boolean
  priorityRight: boolean
  rowHeight: number | null
}) {
  const colClass =
    colTemplate === '50-50'
      ? 'grid-cols-2'
      : colTemplate === '60-40'
        ? 'grid-cols-[3fr_2fr]'
        : 'grid-cols-[2fr_3fr]'

  return (
    <div
      className="relative w-full min-w-0"
      style={
        rowHeight != null && rowHeight > 0
          ? { height: rowHeight, minHeight: rowHeight }
          : { minHeight: 200 }
      }
    >
      <div
        className={cn(
          'absolute inset-0 grid min-h-0 min-w-0 gap-2',
          colClass,
        )}
      >
        <div className={cn('min-h-0 min-w-0 overflow-hidden', VAULT_MODULE_IMAGE_CLASS)}>
          {/* eslint-disable-next-line @next/next/no-img-element -- URLs présignées / externes */}
          <img
            src={left.url}
            alt={left.alt?.trim() || ''}
            className="h-full w-full min-h-0 object-cover"
            loading={priorityLeft ? 'eager' : 'lazy'}
            decoding="async"
          />
        </div>
        <div className={cn('min-h-0 min-w-0 overflow-hidden', VAULT_MODULE_IMAGE_CLASS)}>
          {/* eslint-disable-next-line @next/next/no-img-element -- URLs présignées / externes */}
          <img
            src={right.url}
            alt={right.alt?.trim() || ''}
            className="h-full w-full min-h-0 object-cover"
            loading={priorityRight ? 'eager' : 'lazy'}
            decoding="async"
          />
        </div>
      </div>
    </div>
  )
}

/**
 * Desktop (appelé seulement sous `md:`) : 1ʳᵉ ligne 50/50 = cellules carrées → hauteur de ligne
 * `(L−gap)/2` ; toutes les lignes suivantes réutilisent cette hauteur (motif 50/50 · 60/40 · 40/60).
 */
function DesktopPairedRowGallery({ items }: { items: VaultCarouselResolvedItem[] }) {
  const measureRef = useRef<HTMLDivElement>(null)
  const [rowHeight, setRowHeight] = useState<number | null>(null)

  useLayoutEffect(() => {
    const el = measureRef.current
    if (!el) return
    const update = () => {
      const w = el.getBoundingClientRect().width
      if (w <= 0) return
      // Une colonne 50/50 a la largeur (W − gap) / 2 ; carré → même valeur en hauteur
      setRowHeight((w - DESKTOP_COL_GAP_PX) / 2)
    }
    update()
    const ro = new ResizeObserver(() => update())
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const rows: Array<{
    key: string
    left: VaultCarouselResolvedItem
    right?: VaultCarouselResolvedItem
    pairIndex: number
  }> = []

  for (let i = 0; i < items.length; i += 2) {
    const left = items[i]!
    const right = items[i + 1]
    rows.push({
      key: right ? `${left.mediaId}-${right.mediaId}` : left.mediaId,
      left,
      right,
      pairIndex: Math.floor(i / 2),
    })
  }

  return (
    <div ref={measureRef} className="flex w-full min-w-0 flex-col gap-2">
      {rows.map((row) => {
        if (!row.right) {
          const h = rowHeight && rowHeight > 0 ? rowHeight : 200
          return (
            <div
              key={row.key}
              className="relative w-full min-w-0 overflow-hidden rounded-v-card bg-v-fg-05"
              style={{ height: h, minHeight: h }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- URLs présignées / externes */}
              <img
                src={row.left.url}
                alt={row.left.alt?.trim() || ''}
                className="h-full w-full object-cover"
                loading={row.pairIndex === 0 ? 'eager' : 'lazy'}
                decoding="async"
              />
            </div>
          )
        }

        const cycle = row.pairIndex % 3
        const colTemplate: '50-50' | '60-40' | '40-60' =
          cycle === 0 ? '50-50' : cycle === 1 ? '60-40' : '40-60'
        const start = row.pairIndex * 2

        return (
          <PairedRowTwoImages
            key={row.key}
            left={row.left}
            right={row.right!}
            colTemplate={colTemplate}
            rowHeight={rowHeight}
            priorityLeft={start < 2}
            priorityRight={start + 1 < 2}
          />
        )
      })}
    </div>
  )
}

/** 2+ images, viewport étroit : une image par ligne, empilées (pas de sliding). */
function StackedGallery({ items }: { items: VaultCarouselResolvedItem[] }) {
  return (
    <div className="flex w-full flex-col gap-2">
      {items.map((item, i) => (
        <div key={item.mediaId} className="min-w-0 w-full">
          <CarouselImage item={item} priority={i === 0} />
        </div>
      ))}
    </div>
  )
}

/**
 * - 1 image : pleine largeur.
 * - 2+ : à partir de md, 2 par rangée avec motif 50/50 → 60/40 → 40/60 (répété) ;
 *   sous md, pile verticale 1 / ligne (jamais de carrousel).
 */
export function VaultMediaCarousel({ moduleTitle, description, items }: Props) {
  if (!items.length) return null

  const title = moduleTitle?.trim()
  const desc = description?.trim()
  const count = items.length

  return (
    <div className="w-full space-y-4">
      {title ? (
        <h2 className={`mb-1 ${SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}`}>{title}</h2>
      ) : null}
      {desc ? (
        <p className={`mx-auto max-w-3xl text-center ${VAULT_MODULE_DESCRIPTION_TYPO}`}>{desc}</p>
      ) : null}

      {count === 1 ? (
        <SingleImageLayout item={items[0]!} />
      ) : (
        <>
          <div className={`hidden ${MD_BREAKPOINT}:block`}>
            <DesktopPairedRowGallery items={items} />
          </div>
          <div className={`block ${MD_BREAKPOINT}:hidden`}>
            <StackedGallery items={items} />
          </div>
        </>
      )}
    </div>
  )
}
