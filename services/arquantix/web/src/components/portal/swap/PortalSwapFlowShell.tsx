'use client'

import type { ReactNode } from 'react'
import { ArrowLeft } from 'lucide-react'

import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'

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
        <header className="flex shrink-0 items-center gap-3">
          {onBack ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-9 w-9 shrink-0 rounded-full border-v-border bg-v-card shadow-v-subtle"
              onClick={onBack}
              aria-label="Retour"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          ) : (
            <span className="w-9" />
          )}
          <h1 className="m-0 flex-1 text-center font-ui text-[16px] font-semibold text-v-fg">{title}</h1>
          <span className="w-9" />
        </header>
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
