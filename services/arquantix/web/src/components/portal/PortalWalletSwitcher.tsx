'use client'

import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Wallet } from 'lucide-react'
import { formatPortalWalletAddressShort } from '@/lib/portal/buildPortalWalletScopes'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import { notifyPortalScopeChanged } from '@/lib/portal/portalScopeReload'
import { NAV_PRIMARY_LINK_TYPO } from '@/components/design-system/nav-primary-link'
import { cn } from '@/lib/utils'

type PortalWalletSwitcherProps = {
  variant?: 'toolbar-pill' | 'drawer-row'
  linkColor?: string
}

function scopeSubtitle(scope: PortalWalletScope): string {
  return `${scope.shortLabel} · ${formatPortalWalletAddressShort(scope.address)}`
}

export function PortalWalletSwitcher({
  variant = 'toolbar-pill',
  linkColor,
}: PortalWalletSwitcherProps) {
  const { walletScope, walletScopeId, setWalletScopeId, scopes, loading } =
    usePortalWalletScopeContext()
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

  if (!loading && scopes.length === 0) {
    return null
  }

  const canOpen = scopes.length > 0 && !loading

  const toggleOpen = () => {
    if (!canOpen) return
    setIsOpen((open) => !open)
  }

  const handleScopeChange = (nextId: string) => {
    if (nextId === walletScopeId) {
      setIsOpen(false)
      return
    }
    setWalletScopeId(nextId)
    setIsOpen(false)
    notifyPortalScopeChanged()
  }

  const pillLabel = loading
    ? '…'
    : walletScope
      ? walletScope.shortLabel
      : 'Wallet'

  const listboxPanel = (
    <div
      className="overflow-hidden rounded-xl border border-black/10 bg-white py-1 shadow-lg"
      role="listbox"
      aria-label="Wallet actif"
    >
      {scopes.map((scope) => (
        <button
          key={scope.id}
          type="button"
          role="option"
          aria-selected={scope.id === walletScopeId}
          onClick={() => handleScopeChange(scope.id)}
          className={cn(
            'flex w-full flex-col gap-0.5 px-4 py-2.5 text-left transition-colors hover:bg-black/[0.04]',
            scope.id === walletScopeId && 'bg-black/[0.02]',
          )}
        >
          <span className="flex items-center justify-between gap-3">
            <span className="font-ui text-[15px] font-semibold leading-none text-[#62656E]">
              {scope.label}
            </span>
            <span
              className="flex h-4 w-4 shrink-0 items-center justify-center text-[#0f766e]"
              aria-hidden
            >
              {scope.id === walletScopeId ? (
                <Check className="h-4 w-4" strokeWidth={2.25} />
              ) : null}
            </span>
          </span>
          <span className="font-ui text-[12px] leading-snug text-[#62656E]/80">
            {scopeSubtitle(scope)}
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
          onClick={toggleOpen}
          disabled={!canOpen}
          className={cn(
            NAV_PRIMARY_LINK_TYPO,
            'flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left text-[#62656E] transition-colors hover:bg-[#F3F3F3] hover:text-black',
            isOpen && 'bg-[#F3F3F3] text-black',
          )}
          aria-label="Choisir le wallet actif"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className="flex min-w-0 flex-1 items-center gap-2.5">
            <Wallet className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden />
            <span className="min-w-0 truncate">
              {walletScope ? scopeSubtitle(walletScope) : 'Chargement…'}
            </span>
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
        {isOpen && canOpen ? (
          <div className="border-t border-black/[0.04] bg-[#FAFAFA] p-2">{listboxPanel}</div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={toggleOpen}
        disabled={!canOpen}
        className={cn(
          'inline-flex h-9 max-w-[9.5rem] shrink-0 items-center gap-1.5 rounded-v-pill px-3 font-ui text-[13px] font-medium transition-colors duration-v-fast hover:bg-v-fg-05',
          isOpen && 'bg-v-fg-05',
        )}
        style={{ color: linkColor }}
        aria-label={
          walletScope
            ? `Wallet : ${scopeSubtitle(walletScope)}`
            : 'Wallet actif'
        }
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <Wallet className="h-3.5 w-3.5 shrink-0 opacity-80" strokeWidth={1.75} aria-hidden />
        <span className="truncate">{pillLabel}</span>
        <ChevronDown
          className={cn('h-3.5 w-3.5 shrink-0 opacity-70 transition-transform', isOpen && 'rotate-180')}
          strokeWidth={2}
          aria-hidden
        />
      </button>

      {isOpen && canOpen ? (
        <div className="absolute right-0 top-full z-50 mt-3 w-[min(100vw-2rem,280px)]">
          {listboxPanel}
        </div>
      ) : null}
    </div>
  )
}
