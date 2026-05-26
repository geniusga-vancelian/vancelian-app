'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Bell,
  HelpCircle,
  Inbox,
  Languages,
  MessageSquare,
  Newspaper,
  School,
  Shield,
} from 'lucide-react'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import {
  PortalSectionTitle,
  PortalSettingsCard,
  PortalSettingsRow,
} from '@/components/portal/profile/PortalProfileUi'
import { PortalProfileWalletsSection } from '@/components/portal/profile/PortalProfileWalletsSection'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalProfileSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalSignOutButton } from '@/components/portal/PortalSignOutButton'
import { Container } from '@/components/ui/Container'
import type { PortalDashboardProfile } from '@/lib/portal/dashboardTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

const PROFILE_CACHE_KEY = 'portal:profile'

type ProfilePayload = {
  profile: PortalDashboardProfile | null
}

function CurrencyChip({
  label,
  selected,
  disabled,
  onSelect,
}: {
  label: string
  selected: boolean
  disabled?: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'flex-1 rounded-v-input border px-4 py-3.5 font-ui text-[15px] font-semibold transition-colors duration-v-fast disabled:opacity-50',
        selected
          ? 'border-v-fg bg-v-fg text-white'
          : 'border-v-fg-10 bg-v-bg text-v-fg hover:border-v-fg-20',
      )}
    >
      {label}
    </button>
  )
}

function resolveEmail(profile: PortalDashboardProfile | null): string {
  return profile?.email?.trim() || 'Gérer mon profil'
}

function resolveInitials(profile: PortalDashboardProfile | null): string {
  const fromProfile = profile?.initials?.trim()
  if (fromProfile) return fromProfile.slice(0, 2).toUpperCase()
  const first = profile?.personal?.first_name?.trim().charAt(0) ?? ''
  const last = profile?.personal?.last_name?.trim().charAt(0) ?? ''
  const combined = `${first}${last}`.toUpperCase()
  if (combined) return combined
  const email = profile?.email?.trim()
  if (email) return email.charAt(0).toUpperCase()
  return '?'
}

export function PortalProfileScreen() {
  const { data, loading, error } = usePortalCachedScreen<ProfilePayload>({
    cacheKey: PROFILE_CACHE_KEY,
    url: '/api/portal/profile',
    ttlMs: 120_000,
    errorMessage: 'Unable to load your profile.',
  })
  const [currency, setCurrency] = useState<'EUR' | 'USD'>('EUR')
  const [updatingCurrency, setUpdatingCurrency] = useState(false)
  const [emailNotifications, setEmailNotifications] = useState(false)

  useEffect(() => {
    if (!data?.profile) return
    const ref = data.profile.reference_currency?.trim().toUpperCase()
    if (ref === 'USD' || ref === 'EUR') setCurrency(ref)
  }, [data])

  useEffect(() => {
    if (typeof window === 'undefined' || window.location.hash !== '#wallets') return
    const scrollToWallets = () => {
      document.getElementById('wallets')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    const frame = window.requestAnimationFrame(scrollToWallets)
    return () => window.cancelAnimationFrame(frame)
  }, [loading, data])

  const initials = useMemo(() => resolveInitials(data?.profile ?? null), [data])

  const updateCurrency = async (next: 'EUR' | 'USD') => {
    if (next === currency || updatingCurrency) return
    setUpdatingCurrency(true)
    try {
      const res = await fetch('/api/portal/profile/reference-currency', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reference_currency: next }),
      })
      if (res.ok) setCurrency(next)
    } finally {
      setUpdatingCurrency(false)
    }
  }

  if (loading && !data) {
    return <PortalProfileSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] items-center justify-center py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
      </Container>
    )
  }

  return (
    <PortalPageContainer>
      <div className="mx-auto flex max-w-2xl flex-col gap-8">
        <PortalReveal index={0}>
          <header className="flex flex-col gap-1">
            <AppEyebrow>Account</AppEyebrow>
            <h1 className="m-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg">Profil</h1>
          </header>
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalSettingsCard>
            <PortalSettingsRow
              title="Mon compte"
              subtitle={resolveEmail(data?.profile ?? null)}
              href="#"
              leading={
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#E5E5EA] font-ui text-[14px] font-semibold text-[#3C3C43]">
                  {initials}
                </span>
              }
            />
          </PortalSettingsCard>
        </PortalReveal>

        <PortalReveal index={2}>
          <section className="flex flex-col gap-3">
            <PortalSectionTitle>Devise de référence</PortalSectionTitle>
            <PortalSettingsCard className="p-4 sm:p-5">
              <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
                Les prix et valorisations seront affichés dans la devise choisie.
              </p>
              <div className="mt-4 flex gap-2">
                <CurrencyChip
                  label="EUR (€)"
                  selected={currency === 'EUR'}
                  disabled={updatingCurrency}
                  onSelect={() => void updateCurrency('EUR')}
                />
                <CurrencyChip
                  label="USD ($)"
                  selected={currency === 'USD'}
                  disabled={updatingCurrency}
                  onSelect={() => void updateCurrency('USD')}
                />
              </div>
            </PortalSettingsCard>
          </section>
        </PortalReveal>

        <PortalReveal index={3}>
          <PortalProfileWalletsSection />
        </PortalReveal>

        <PortalReveal index={4}>
          <section className="flex flex-col gap-3">
            <PortalSectionTitle>Paramètres</PortalSectionTitle>
            <PortalSettingsCard>
              <PortalSettingsRow
                title="Sécurité"
                subtitle="Méthodes de connexion, appareils"
                leading={<Shield className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Notifications"
                subtitle="Toutes les alertes sur cet appareil"
                leading={<Bell className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Langue"
                subtitle="FR"
                leading={<Languages className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Notifications email"
                subtitle="Newsletters & rapports"
                trailing={
                  <button
                    type="button"
                    role="switch"
                    aria-checked={emailNotifications}
                    onClick={() => setEmailNotifications((value) => !value)}
                    className={cn(
                      'relative h-7 w-12 shrink-0 rounded-v-pill border-0 transition-colors duration-v-fast',
                      emailNotifications ? 'bg-v-fg' : 'bg-v-fg-20',
                    )}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-v-subtle transition-transform duration-v-fast',
                        emailNotifications ? 'translate-x-[22px]' : 'translate-x-0.5',
                      )}
                    />
                  </button>
                }
              />
            </PortalSettingsCard>
          </section>
        </PortalReveal>

        <PortalReveal index={5}>
          <section className="flex flex-col gap-3">
            <PortalSectionTitle>Support</PortalSectionTitle>
            <PortalSettingsCard>
              <PortalSettingsRow
                title="Centre d'aide"
                href="/help"
                leading={<HelpCircle className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Academy"
                href={PORTAL_ROUTES.academy}
                leading={<School className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Blog"
                href="/blog"
                leading={<Newspaper className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Assistance de compte sur mesure"
                href="/help"
                leading={<MessageSquare className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
              <PortalSettingsRow
                title="Boîte de réception"
                leading={<Inbox className="h-6 w-6 text-v-fg" strokeWidth={1.75} />}
              />
            </PortalSettingsCard>
          </section>
        </PortalReveal>

        <PortalReveal index={6}>
          <section className="flex flex-col gap-3">
            <PortalSectionTitle>Informations</PortalSectionTitle>
            <PortalSettingsCard>
              <PortalSettingsRow title="Conditions générales" />
              <PortalSettingsRow title="Politique de confidentialité" />
              <PortalSettingsRow title="Version" subtitle="Web portal" trailing={null} />
            </PortalSettingsCard>
          </section>
        </PortalReveal>

        <PortalReveal index={7}>
          <section className="flex flex-col gap-3 pt-2">
            <PortalSignOutButton variant="profile" />
          </section>
        </PortalReveal>
      </div>
    </PortalPageContainer>
  )
}
