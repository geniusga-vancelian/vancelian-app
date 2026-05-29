'use client'

import { useState } from 'react'
import { Banknote, Home, Users } from 'lucide-react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  PortalPlacerBasketCard,
  PortalPlacerBundleCoffreCard,
  PortalPlacerCoffreCard,
  PortalPlacerSectionHead,
  PortalPlacerSeeAll,
  resolveCurrencyIcon,
} from '@/components/portal/bundles/PortalPlacerBundleCards'
import { PortalLazyBundleInvestDialog } from '@/components/portal/bundles/PortalLazyBundleInvestDialog'
import { PortalLazyEarnVaultModal } from '@/components/portal/invest/PortalLazyEarnVaultModal'
import { PortalLazyLedgityVaultModal } from '@/components/portal/invest/PortalLazyLedgityVaultModal'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { resolveExclusiveOfferCoverUrl } from '@/lib/portal/exclusiveOfferPlaceholderImages'
import { formatEarnApyFromBps as formatLedgityApyFromBps } from '@/lib/portal/ledgity/ledgityVaultFormat'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { formatEarnApyFromBps, formatEarnUsd } from '@/lib/portal/morphoVaultFormat'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import { cn } from '@/lib/utils'

export type PlacerFilterId = 'all' | 'coffres' | 'offres' | 'paniers'
export { isPlacerCoffreBundle } from '@/components/portal/bundles/PortalPlacerBundleCards'

const PLACER_FILTERS: { id: PlacerFilterId; label: string }[] = [
  { id: 'all', label: 'Tout' },
  { id: 'coffres', label: 'Coffres' },
  { id: 'offres', label: 'Offres exclu.' },
  { id: 'paniers', label: 'Paniers crypto' },
]

function formatDurationMonths(months: number | null): string | null {
  if (months == null || months <= 0) return null
  return `${months}M`
}

type VaultUnion = PortalMorphoVaultDetails | PortalLedgityVaultDetails

function isLedgityVault(vault: VaultUnion): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

export function PortalPlacerFilter({
  value,
  onChange,
}: {
  value: PlacerFilterId
  onChange: (id: PlacerFilterId) => void
}) {
  return (
    <div className="placer-filter">
      <div className="seg seg--md" role="tablist" aria-label="Filtrer les placements">
        {PLACER_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            role="tab"
            aria-selected={value === f.id}
            className={cn('seg__item', value === f.id && 'is-on')}
            onClick={() => onChange(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PortalPlacerBanner({ offer }: { offer: PortalExclusiveOffer | null }) {
  const isNiseko = offer?.slug.toLowerCase().includes('niseko')
  const href = offer?.href ?? '/app/invest'
  const imageUrl =
    offer?.coverUrl ||
    (isNiseko ? '/app-ds/assets/photos/niseko-entrance.jpg' : undefined)

  return (
    <PortalNavLink
      href={href}
      className="mkt no-underline"
      style={imageUrl ? { backgroundImage: `url('${imageUrl}')` } : undefined}
    >
      <span className="mkt__scrim" aria-hidden />
      <h2 className="mkt__title">
        {isNiseko ? (
          <>
            <span className="mkt__title-ui">La beauté </span>
            <span className="mkt__title-ed">du Japon</span>
          </>
        ) : (
          <span className="mkt__title-ui">{offer?.title ?? 'Découvrir nos offres'}</span>
        )}
      </h2>
      <p className="mkt__sub">
        {isNiseko
          ? 'Lodge Niseko Hokkaidō · Hôtellerie de montagne, rendement 6,2 %'
          : offer?.subtitle || offer?.description || 'Sélection d’actifs tokenisés'}
      </p>
      <span className="btn btn--white mkt__cta">
        Découvrir l&apos;offre
        <KalaiIcon name="arrow-right" size={16} className="text-current" />
      </span>
    </PortalNavLink>
  )
}

function PortalPlacerOfferCard({ offer }: { offer: PortalExclusiveOffer }) {
  const pct = Math.round(offer.progressPct)
  const cover = resolveExclusiveOfferCoverUrl(offer.coverUrl, offer.id)
  const ticket =
    formatDurationMonths(offer.durationMonths) ??
    (offer.apyLabel !== '—' ? offer.apyLabel : offer.targetLabel)

  return (
    <PortalNavLink href={offer.href} className="offer offer--sq offer--link no-underline">
      <div className="offer__media offer__media--sq">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="offer__img" src={cover} alt="" />
        <span className="offer__cat">
          <Home aria-hidden className="h-3.5 w-3.5" />
          {offer.category}
        </span>
        <div className="offer__chips">
          <span className="o-chip">
            <Users aria-hidden className="h-3.5 w-3.5" />
            {offer.investorsCount}
          </span>
          <span className="o-chip o-chip--progress">
            {offer.raisedLabel}
            <span className="o-chip__bar">
              <span style={{ width: `${pct}%` }} />
            </span>
          </span>
          <span className="o-chip">
            <Banknote aria-hidden className="h-3.5 w-3.5" />
            {ticket}
          </span>
        </div>
      </div>
      <div className="offer__body">
        <div className="offer__text">
          <h3 className="offer__title">{offer.title}</h3>
          <p className="offer__desc">{offer.subtitle || offer.description}</p>
        </div>
        <span className="btn btn--primary offer__cta">
          {offer.isFunded ? 'Voir' : 'Investir'}
        </span>
      </div>
    </PortalNavLink>
  )
}

/** @deprecated Utiliser PortalAdvisorBanner depuis @/components/portal/PortalAdvisorBanner */
export function PortalPlacerAdvisorBanner() {
  return <PortalAdvisorBanner />
}

type Props = {
  offers: PortalExclusiveOffer[]
  coffreBundles: PortalCryptoBundle[]
  panierBundles: PortalCryptoBundle[]
  defiVaults?: VaultUnion[]
  showDeFiVaults?: boolean
}

export function PortalPlacerView({
  offers,
  coffreBundles,
  panierBundles,
  defiVaults = [],
  showDeFiVaults = false,
}: Props) {
  const [filter, setFilter] = useState<PlacerFilterId>('all')
  const [investBundle, setInvestBundle] = useState<PortalCryptoBundle | null>(null)
  const [morphoVault, setMorphoVault] = useState<PortalMorphoVaultDetails | null>(null)
  const [ledgityVault, setLedgityVault] = useState<PortalLedgityVaultDetails | null>(null)

  const show = (key: PlacerFilterId) => filter === 'all' || filter === key

  const bannerOffer =
    offers.find((o) => o.slug.toLowerCase().includes('niseko')) ?? offers[0] ?? null

  const coffreCards = [
    ...coffreBundles.map((bundle) => ({
      key: `bundle-${bundle.id}`,
      kind: 'bundle' as const,
      bundle,
    })),
    ...(showDeFiVaults
      ? defiVaults.map((vault) => ({
          key: `vault-${vault.id}`,
          kind: 'defi' as const,
          title: vault.name,
          description: vault.description ?? '',
          photo: '/app-ds/assets/photos/coffre-flex.png',
          perf: isLedgityVault(vault)
            ? formatLedgityApyFromBps(vault.userApyBps)
            : formatEarnApyFromBps(vault.userApyBps),
          liquidity: formatEarnUsd(vault.tvlUsd),
          currency: vault.asset.symbol,
          currencyIcon: resolveCurrencyIcon(vault.asset.symbol),
          categoryIcon: 'vault' as const,
          href: undefined,
          onInvest: () => {
            if (isLedgityVault(vault)) setLedgityVault(vault)
            else setMorphoVault(vault)
          },
        }))
      : []),
  ]

  return (
    <>
      <div className="portal-placer-grid">
        <div className="col-main">
          <PortalPlacerBanner offer={bannerOffer} />
          <PortalPlacerFilter value={filter} onChange={setFilter} />

          {show('coffres') && coffreCards.length > 0 ? (
            <div id="placer-coffres">
              <PortalPlacerSectionHead
                title="Coffres"
                desc="Une réserve productive, choisie selon votre horizon."
                action={<PortalPlacerSeeAll href="#placer-coffres">Voir tous les coffres</PortalPlacerSeeAll>}
              />
              <div className="placer-grid placer-grid--2">
                {coffreCards.map((card) => {
                  if (card.kind === 'bundle') {
                    return (
                      <PortalPlacerBundleCoffreCard
                        key={card.key}
                        bundle={card.bundle}
                        onInvest={() => setInvestBundle(card.bundle)}
                      />
                    )
                  }
                  const { key, kind: _kind, ...defiCard } = card
                  return <PortalPlacerCoffreCard key={key} {...defiCard} />
                })}
              </div>
            </div>
          ) : null}

          {show('offres') && offers.length > 0 ? (
            <div id="placer-offres">
              <PortalPlacerSectionHead
                title="Offres exclusives"
                desc="Une sélection mensuelle d'actifs tokenisés, instruits par notre comité."
                action={<PortalPlacerSeeAll href="#placer-offres">Voir toutes les offres</PortalPlacerSeeAll>}
              />
              <div className="placer-grid placer-grid--2">
                {offers.map((offer) => (
                  <PortalPlacerOfferCard key={offer.id} offer={offer} />
                ))}
              </div>
            </div>
          ) : null}

          {show('paniers') && panierBundles.length > 0 ? (
            <div id="placer-paniers">
              <PortalPlacerSectionHead
                title="Paniers crypto"
                desc="Des expositions thématiques rééquilibrées chaque mois."
                action={<PortalPlacerSeeAll href="#placer-paniers">Voir tous les paniers</PortalPlacerSeeAll>}
              />
              <div className="placer-grid placer-grid--2">
                {panierBundles.map((bundle) => (
                  <PortalPlacerBasketCard
                    key={bundle.id}
                    bundle={bundle}
                    onInvest={() => setInvestBundle(bundle)}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <aside className="col-side">
          <PortalPlacerAdvisorBanner />
        </aside>
      </div>

      {investBundle ? (
        <PortalLazyBundleInvestDialog
          bundle={investBundle}
          open
          onOpenChange={(open) => {
            if (!open) setInvestBundle(null)
          }}
        />
      ) : null}

      {morphoVault ? (
        <PortalLazyEarnVaultModal vault={morphoVault} onClose={() => setMorphoVault(null)} />
      ) : null}

      {ledgityVault ? (
        <PortalLazyLedgityVaultModal vault={ledgityVault} onClose={() => setLedgityVault(null)} />
      ) : null}
    </>
  )
}
