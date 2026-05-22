'use client'

import * as React from 'react'
import type { PortalSupportContent } from '@/lib/cms/portal-support'
import { getDefaultPortalSupportContent } from '@/lib/cms/portal-support'

const PortalSupportContentContext = React.createContext<PortalSupportContent>(
  getDefaultPortalSupportContent(),
)

export function PortalSupportContentProvider({
  content,
  children,
}: {
  content: PortalSupportContent
  children: React.ReactNode
}) {
  return (
    <PortalSupportContentContext.Provider value={content}>
      {children}
    </PortalSupportContentContext.Provider>
  )
}

export function usePortalSupportContent(): PortalSupportContent {
  return React.useContext(PortalSupportContentContext)
}
