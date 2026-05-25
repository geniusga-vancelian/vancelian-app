'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Layers } from 'lucide-react'
import {
  PORTAL_CHAINS,
  PORTAL_CHAIN_LABELS,
  PORTAL_CHAIN_SHORT,
  type PortalChain,
} from '@/config/portalChains'
import { NAV_PRIMARY_LINK_TYPO } from '@/components/design-system/nav-primary-link'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { notifyPortalScopeChanged } from '@/lib/portal/portalScopeReload'
import { cn } from '@/lib/utils'

type PortalChainSwitcherProps = {
  /**
   * `toolbar-pill` : libellé court + chevron (navbar desktop portail).
   * `drawer-row` : ligne pleine largeur (menu mobile).
   */
  variant?: 'toolbar-pill' | 'drawer-row'
  /** Couleur texte héritée de la topnav. */
  linkColor?: string
}

const CHAIN_DOT_CLASS: Record<PortalChain, string> = {
  base: 'bg-[#0052FF]',
  ethereum: 'bg-[#627EEA]',
  solana: 'bg-gradient-to-br from-[#9945FF] to-[#14F195]',
}

export function PortalChainSwitcher({
  variant = 'toolbar-pill',
  linkColor,
}: PortalChainSwitcherProps) {
  const { chain, setChain } = usePortalChainContext()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleChainChange = (next: PortalChain) => {
    if (next === chain) {
      setIsOpen(false)
      return
    }
    setChain(next)
    setIsOpen(false)
    notifyPortalScopeChanged()
  }

  const listboxPanel = (
    <div
      className="overflow-hidden rounded-xl border border-black/10 bg-white py-1 shadow-lg"
      role="listbox"
      aria-label="Réseau blockchain"
    >
      {PORTAL_CHAINS.map((item) => (
        <button
          key={item}
          type="button"
          role="option"
          aria-selected={item === chain}
          onClick={() => handleChainChange(item)}
          className={cn(
            'flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left font-ui font-semibold text-[15px] leading-none tracking-normal text-[#62656E] transition-colors hover:bg-black/[0.04] hover:text-black',
            item === chain && 'text-black',
          )}
        >
          <span className="flex min-w-0 items-center gap-2.5">
            <span
              className={cn('h-2.5 w-2.5 shrink-0 rounded-full', CHAIN_DOT_CLASS[item])}
              aria-hidden
            />
            <span>{PORTAL_CHAIN_LABELS[item]}</span>
          </span>
          <span
            className="flex h-4 w-4 shrink-0 items-center justify-center text-[#0f766e]"
            aria-hidden
          >
            {item === chain ? <Check className="h-4 w-4" strokeWidth={2.25} /> : null}
          </span>
        </button>
      ))}
    </div>
  )

  if (variant === 'drawer-row') {
    return (
      <div className="relative border-b border-black/[0.06]" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            NAV_PRIMARY_LINK_TYPO,
            'flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left text-[#62656E] transition-colors hover:bg-[#F3F3F3] hover:text-black',
            isOpen && 'bg-[#F3F3F3] text-black',
          )}
          aria-label="Choisir le réseau blockchain"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className="flex min-w-0 flex-1 items-center gap-2.5">
            <Layers className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden />
            <span className="min-w-0">{PORTAL_CHAIN_LABELS[chain]}</span>
          </span>
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-[#62656E] transition-transform duration-200',
              isOpen && 'rotate-180',
            )}
            strokeWidth={2}
            aria-hidden
          />
        </button>
        {isOpen ? <div className="border-t border-black/[0.04] bg-[#FAFAFA] p-2">{listboxPanel}</div> : null}
      </div>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-v-pill px-3 font-ui text-[13px] font-medium transition-colors duration-v-fast hover:bg-v-fg-05',
          isOpen && 'bg-v-fg-05',
        )}
        style={{ color: linkColor }}
        aria-label={`Réseau : ${PORTAL_CHAIN_LABELS[chain]}`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span
          className={cn('h-2 w-2 shrink-0 rounded-full', CHAIN_DOT_CLASS[chain])}
          aria-hidden
        />
        <span>{PORTAL_CHAIN_SHORT[chain]}</span>
        <ChevronDown
          className={cn('h-3.5 w-3.5 shrink-0 opacity-70 transition-transform', isOpen && 'rotate-180')}
          strokeWidth={2}
          aria-hidden
        />
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-full z-50 mt-3 w-[min(100vw-2rem,220px)]">
          {listboxPanel}
        </div>
      ) : null}
    </div>
  )
}