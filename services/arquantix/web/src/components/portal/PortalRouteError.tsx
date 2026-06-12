'use client'

import { useEffect } from 'react'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalNavLink } from '@/components/portal/PortalNavLink'

type Props = {
  error: Error & { digest?: string }
  reset: () => void
  /** Message affiché à l'utilisateur (le détail technique reste dans la console). */
  message?: string
  backHref?: string
  backLabel?: string
}

/**
 * Garde d'erreur gracieuse pour un segment de route SSR : remplace l'écran
 * d'erreur Next.js par un message + bouton « Try again » (re-render du segment)
 * et un retour optionnel, sans casser le shell.
 */
export function PortalRouteError({ error, reset, message, backHref, backLabel }: Props) {
  useEffect(() => {
    console.error('[portal route error]', error)
  }, [error])

  return (
    <PortalPageContainer className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10 text-center">
      <p className="m-0 max-w-md font-ui text-[15px] leading-relaxed text-v-fg">
        {message ?? 'Something went wrong while loading this page.'}
      </p>
      <div className="flex items-center gap-5">
        <button
          type="button"
          onClick={() => reset()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Try again
        </button>
        {backHref ? (
          <PortalNavLink href={backHref} className="font-ui text-[14px] text-v-fg-muted no-underline">
            {backLabel ?? 'Go back'}
          </PortalNavLink>
        ) : null}
      </div>
    </PortalPageContainer>
  )
}
