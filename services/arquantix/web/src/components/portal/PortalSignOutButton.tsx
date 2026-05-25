'use client'

import { useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  portalLogoutRedirectHref,
  primePortalLogoutClientState,
} from '@/lib/portal/navigateToPortalLogin'

type Props = {
  className?: string
  /** `profile` — bouton pleine largeur noir DS ; `compact` — pastille navbar (legacy). */
  variant?: 'compact' | 'profile'
}

/** Sign out portail — flèche → loader au clic. */
export function PortalSignOutButton({ className, variant = 'compact' }: Props) {
  const loggingOutRef = useRef(false)
  const [loggingOut, setLoggingOut] = useState(false)

  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    if (loggingOutRef.current) return
    loggingOutRef.current = true
    setLoggingOut(true)
    primePortalLogoutClientState()
    window.location.href = portalLogoutRedirectHref()
  }

  return (
    <a
      href={portalLogoutRedirectHref()}
      onClick={handleClick}
      aria-busy={loggingOut || undefined}
      className={cn(
        'group items-center justify-center gap-2 no-underline transition-[opacity,background-color] duration-v-fast ease-v-out',
        variant === 'profile'
          ? 'flex h-11 w-full rounded-v-pill bg-v-fg px-4 font-ui text-[15px] font-semibold leading-none text-white hover:opacity-90 active:opacity-95'
          : cn(
              'inline-flex h-9 shrink-0 rounded-v-pill bg-v-fg-05 px-3 font-ui text-[13px] font-medium leading-none text-v-fg',
              'hover:bg-v-fg-10 active:bg-v-fg-10',
            ),
        loggingOut && 'pointer-events-none',
        className,
      )}
    >
      <span>Sign out</span>
      {loggingOut ? (
        <Loader2 className="h-4 w-4 shrink-0 animate-spin" aria-hidden />
      ) : (
        <span
          className="inline-block transition-transform duration-v-base ease-v-out group-hover:translate-x-1"
          aria-hidden="true"
        >
          →
        </span>
      )}
      {loggingOut ? <span className="sr-only">Signing out</span> : null}
    </a>
  )
}
