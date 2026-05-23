'use client'

import { useEffect, useState } from 'react'
import { Wallet } from 'lucide-react'

import { PortalSectionTitle, PortalSettingsCard } from '@/components/portal/profile/PortalProfileUi'

type PrivyBalance = {
  asset: string
  balance: string
  available_balance: string
  wallet_address?: string | null
}

type PrivyDeposit = {
  id: string
  asset: string
  amount: string
  title: string
  status: string
  created_at: string
}

export function PortalPrivyWalletSection() {
  const [balances, setBalances] = useState<PrivyBalance[]>([])
  const [deposits, setDeposits] = useState<PrivyDeposit[]>([])
  const [loading, setLoading] = useState(true)
  const [unauthorized, setUnauthorized] = useState(false)

  useEffect(() => {
    let cancelled = false

    ;(async () => {
      try {
        const [balancesRes, depositsRes] = await Promise.all([
          fetch('/api/portal/privy-wallet/balances', { cache: 'no-store' }),
          fetch('/api/portal/privy-wallet/deposits?limit=5', { cache: 'no-store' }),
        ])

        if (balancesRes.status === 401 || depositsRes.status === 401) {
          if (!cancelled) {
            setUnauthorized(true)
            setLoading(false)
          }
          return
        }

        if (balancesRes.ok) {
          const payload = (await balancesRes.json()) as { balances?: PrivyBalance[] }
          if (!cancelled) setBalances(payload.balances ?? [])
        }

        if (depositsRes.ok) {
          const payload = (await depositsRes.json()) as { deposits?: PrivyDeposit[] }
          if (!cancelled) setDeposits(payload.deposits ?? [])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  if (unauthorized || loading) return null
  if (balances.length === 0 && deposits.length === 0) return null

  return (
    <section className="space-y-3">
      <PortalSectionTitle>Wallet crypto Privy</PortalSectionTitle>
      <p className="m-0 text-sm text-v-fg-60">
        Ces soldes sont inclus dans la ligne Crypto du dashboard et du patrimoine total.
      </p>
      <PortalSettingsCard>
        {balances.length > 0 ? (
          <div className="space-y-3 border-b border-v-fg-10 px-4 py-4">
            <p className="m-0 flex items-center gap-2 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-50">
              <Wallet className="h-4 w-4" aria-hidden />
              Soldes
            </p>
            <ul className="m-0 list-none space-y-2 p-0">
              {balances.map((row) => (
                <li
                  key={`${row.asset}-${row.wallet_address ?? ''}`}
                  className="flex items-center justify-between gap-3 font-ui text-[15px]"
                >
                  <span className="font-semibold text-v-fg">{row.asset}</span>
                  <span className="text-v-fg-70">
                    {row.balance} <span className="text-v-fg-40">(dispo. {row.available_balance})</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {deposits.length > 0 ? (
          <div className="space-y-3 px-4 py-4">
            <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-50">
              Dépôts récents
            </p>
            <ul className="m-0 list-none space-y-2 p-0">
              {deposits.map((row) => (
                <li key={row.id} className="flex items-start justify-between gap-3 font-ui text-[14px]">
                  <div>
                    <p className="m-0 font-medium text-v-fg">{row.title}</p>
                    <p className="m-0 text-v-fg-40">
                      {new Date(row.created_at).toLocaleString('fr-FR')} · {row.status}
                    </p>
                  </div>
                  <span className="shrink-0 font-semibold text-v-fg">
                    {row.amount} {row.asset}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </PortalSettingsCard>
    </section>
  )
}
