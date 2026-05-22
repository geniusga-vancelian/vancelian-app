'use client'

import * as React from 'react'
import { VProofPress } from '@/components/design-system/vancelian/VProofPress'

export interface SectionProofPressProps {
  eyebrow?: string
  items?: Array<{ label: string; variant?: 'bfm' | 'tribune' | 'echos' | 'finyear' | 'text' }>
}

export function SectionProofPress({ eyebrow, items }: SectionProofPressProps) {
  return <VProofPress eyebrow={eyebrow} items={items} />
}
