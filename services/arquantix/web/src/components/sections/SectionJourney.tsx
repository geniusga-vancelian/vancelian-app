'use client'

import * as React from 'react'
import { VJourney } from '@/components/design-system/vancelian/VJourney'

export interface SectionJourneyProps {
  pill?: string
  title?: string
  description?: string
  backgroundMediaUrl?: string
  backgroundMediaMimeType?: string
  notificationMessage?: string
  ctas?: Array<{ label: string; href?: string; variant?: 'primary' | 'secondary' }>
}

export function SectionJourney({
  backgroundMediaMimeType,
  ...props
}: SectionJourneyProps) {
  const kind =
    backgroundMediaMimeType?.startsWith('video/') ||
    /\.(mp4|webm|mov)(\?|$)/i.test(props.backgroundMediaUrl || '')
      ? 'video'
      : 'image'

  return <VJourney {...props} backgroundMediaKind={kind} />
}
