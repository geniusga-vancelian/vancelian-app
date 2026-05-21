'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils'
import { BrandLogo } from '@/components/ui/BrandLogo'

type Props = {
  children: React.ReactNode
  className?: string
  showBack?: boolean
  backHref?: string
}

export function PortalAuthShell({
  children,
  className,
  showBack = false,
  backHref = '/app/login',
}: Props) {
  return (
    <div className={cn('flex min-h-screen flex-col bg-v-bg', className)}>
      <header className="flex items-center justify-between px-6 py-5 sm:px-10">
        <Link href="/app/login" className="inline-flex items-center" aria-label="Vancelian">
          <BrandLogo color="black" className="h-6 w-auto" />
        </Link>
        {showBack ? (
          <Link
            href={backHref}
            className="font-ui text-[14px] font-medium text-v-fg-muted transition-colors hover:text-v-fg"
          >
            ← Retour
          </Link>
        ) : (
          <span className="w-12" aria-hidden />
        )}
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-16 pt-4">
        <div className="w-full max-w-[440px]">{children}</div>
      </main>
    </div>
  )
}
