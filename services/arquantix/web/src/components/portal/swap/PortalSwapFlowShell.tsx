'use client'

import type { ReactNode } from 'react'

import { AppTopAppBar } from '@/components/design-system/app/AppTopAppBar'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'

type Props = {
  title?: string
  onBack?: () => void
  children: ReactNode
  footer?: ReactNode
  centered?: boolean
}

export function PortalSwapFlowShell({
  title = 'Swap',
  onBack,
  children,
  footer,
  centered = false,
}: Props) {
  return (
    <PortalPageContainer className="flex flex-1 flex-col">
      <div
        className={`mx-auto flex w-full max-w-lg flex-1 flex-col gap-6 ${footer ? 'pb-6' : ''}`}
      >
        <AppTopAppBar title={title} onBack={onBack} />
        <div className={`flex flex-1 flex-col ${centered ? 'justify-center' : ''}`}>{children}</div>
      </div>
      {footer ? (
        <div className="sticky bottom-0 z-20 shrink-0 border-t border-v-border/60 bg-v-bg px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4">
          <div className="mx-auto w-full max-w-lg">{footer}</div>
        </div>
      ) : null}
    </PortalPageContainer>
  )
}
