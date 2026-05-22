'use client'

import * as React from 'react'
import type { PortalAuthContent } from '@/lib/cms/portal-auth'
import { getDefaultPortalAuthContent } from '@/lib/cms/portal-auth'

const PortalAuthContentContext = React.createContext<PortalAuthContent>(getDefaultPortalAuthContent())

export function PortalAuthContentProvider({
  content,
  children,
}: {
  content: PortalAuthContent
  children: React.ReactNode
}) {
  return (
    <PortalAuthContentContext.Provider value={content}>{children}</PortalAuthContentContext.Provider>
  )
}

export function usePortalAuthContent(): PortalAuthContent {
  return React.useContext(PortalAuthContentContext)
}
