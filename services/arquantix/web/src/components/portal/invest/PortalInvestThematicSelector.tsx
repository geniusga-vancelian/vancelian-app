'use client'

import { useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { cn } from '@/lib/utils'

export type PortalInvestmentCategory = {
  id: string
  slug: string
  label: string
  imageUrl: string | null
}

type Props = {
  selectedSlug: string | null
  onSelect: (slug: string | null) => void
}

type CategoryOption = {
  slug: string | null
  label: string
  imageUrl?: string | null
}

function CategoryChip({
  label,
  imageUrl,
  selected,
  onSelect,
}: {
  label: string
  imageUrl?: string | null
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'inline-flex shrink-0 items-center gap-2 rounded-v-pill border px-4 py-2.5 font-ui text-[14px] font-semibold transition-colors duration-v-fast',
        selected
          ? 'border-v-fg bg-v-fg text-white'
          : 'border-v-fg-10 bg-v-bg text-v-fg hover:border-v-fg-20',
      )}
    >
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl} alt="" className="h-5 w-5 rounded-full object-cover" />
      ) : null}
      {label}
    </button>
  )
}

export function PortalInvestThematicSelector({ selectedSlug, onSelect }: Props) {
  const [categories, setCategories] = useState<PortalInvestmentCategory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/investment-categories', { cache: 'no-store' })
        const json = (await res.json()) as { categories?: PortalInvestmentCategory[] }
        if (!cancelled) setCategories(json.categories ?? [])
      } catch {
        if (!cancelled) setCategories([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const options = useMemo<CategoryOption[]>(
    () => [{ slug: null, label: 'Toutes' }, ...categories.map((c) => ({ slug: c.slug, label: c.label, imageUrl: c.imageUrl }))],
    [categories],
  )

  return (
    <section className="flex flex-col gap-3">
      <PortalSectionHeading title="Thématiques" />
      {loading ? (
        <div className="flex items-center gap-2 font-ui text-[14px] text-v-fg-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Chargement…
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {options.map((option) => (
            <CategoryChip
              key={option.slug ?? 'all'}
              label={option.label}
              imageUrl={option.imageUrl}
              selected={selectedSlug === option.slug}
              onSelect={() => onSelect(option.slug)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
