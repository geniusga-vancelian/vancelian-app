'use client'

import { useEffect, useState } from 'react'
import { PortalNewsWidget } from '@/components/portal/dashboard/PortalNewsWidget'
import type { PortalNewsWidgetData } from '@/lib/portal/parseTop10NewsWidget'

function NewsSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="h-6 w-40 animate-pulse rounded-v-input bg-v-fg-05" />
      <div className="news-deck">
        <div className="h-[180px] w-[min(320px,calc(100%-24px))] shrink-0 animate-pulse rounded-[16px] bg-v-card" />
        <div className="h-[180px] w-[min(320px,calc(100%-24px))] shrink-0 animate-pulse rounded-[16px] bg-v-card" />
      </div>
    </div>
  )
}

type Props = {
  locale?: string
  initialData?: PortalNewsWidgetData | null
}

export function PortalNewsWidgetSection({ locale = 'fr', initialData }: Props) {
  const [data, setData] = useState<PortalNewsWidgetData | null>(initialData ?? null)
  const [loading, setLoading] = useState(!initialData?.items?.length)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (initialData?.items?.length) {
      setData(initialData)
      setLoading(false)
      return
    }

    let cancelled = false
    ;(async () => {
      setLoading(true)
      setFailed(false)
      try {
        const res = await fetch(`/api/portal/news-widget?locale=${encodeURIComponent(locale)}`)
        if (!res.ok) {
          if (!cancelled) {
            setData(null)
            setFailed(true)
          }
          return
        }
        const json = (await res.json()) as PortalNewsWidgetData
        if (!cancelled) setData(json.items?.length ? json : null)
      } catch {
        if (!cancelled) setFailed(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [initialData, locale])

  if (loading) return <NewsSkeleton />
  if (failed || !data) return null

  return <PortalNewsWidget data={data} minReadLabel="min" />
}
