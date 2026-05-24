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
}

/** Sign out portail — fond visible, flèche → loader au clic. */
export function PortalSignOutButton({ className }: Props) {
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
        'group inline-flex h-9 shrink-0 items-center justify-center gap-2',
        'rounded-v-pill bg-v-fg-05 px-3 font-ui text-[13px] font-medium leading-none text-v-fg',
        'no-underline transition-colors duration-v-fast ease-v-out',
        'hover:bg-v-fg-10 active:bg-v-fg-10',
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
