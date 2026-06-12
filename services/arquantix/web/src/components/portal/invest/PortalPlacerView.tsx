'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  PortalPlacerBasketCard,
  PortalPlacerBundleCoffreCard,
  PortalPlacerCoffreCard,
  PortalPlacerSectionHead,
  PortalPlacerSeeAll,
  resolveCurrencyIcon,
} from '@/components/portal/bundles/PortalPlacerBundleCards'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalPlacerSectionSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { resolveExclusiveOfferCoverUrl } from '@/lib/portal/exclusiveOfferPlaceholderImages'
import { formatEarnApyFromBps as formatLedgityApyFromBps } from '@/lib/portal/ledgity/ledgityVaultFormat'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalExclusiveOffer, PortalVaultProduct } from '@/lib/portal/investTypes'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import {
  portalLedgityVaultInvestRoute,
  portalMorphoVaultInvestRoute,
  portalVaultInvestRoute,
  resolvePortalVaultProductInvestRoute,
} from '@/lib/portal/portalRouting'
import { resolvePortalBundleFlowRoute } from '@/lib/portal/resolvePortalBundleFlowRoute'
import { formatEarnApyFromBps, formatEarnUsd } from '@/lib/portal/morphoVaultFormat'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import { cn } from '@/lib/utils'

export type PlacerFilterId = 'all' | 'coffres' | 'offres' | 'paniers'
export { isPlacerCoffreBundle } from '@/components/portal/bundles/PortalPlacerBundleCards'

const PLACER_FILTERS: { id: PlacerFilterId; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'coffres', label: 'Vaults' },
  { id: 'offres', label: 'Exclusive' },
  { id: 'paniers', label: 'Crypto baskets' },
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
      <div className="seg seg--md" role="tablist" aria-label="Filter investments">
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
            <span className="mkt__title-ui">The beauty of </span>
            <span className="mkt__title-ed">Japan</span>
          </>
        ) : (
          <span className="mkt__title-ui">{offer?.title ?? 'Discover our offers'}</span>
        )}
      </h2>
      <p className="mkt__sub">
        {isNiseko
          ? 'Lodge Niseko Hokkaidō · Mountain hospitality, 6.2% yield'
          : offer?.subtitle || offer?.description || 'Curated tokenized assets'}
      </p>
      <span className="btn btn--white mkt__cta">
        View offer
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
  const investHref = portalVaultInvestRoute(offer.slug)
  const withdrawHref = portalVaultInvestRoute(offer.slug, 'withdraw')

  return (
    <article className="offer offer--sq">
      <PortalNavLink href={offer.href} className="offer__media offer__media--sq offer--link no-underline">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="offer__img" src={cover} alt="" />
        <span className="offer__cat">
          <KalaiIcon name="home" size={16} aria-hidden />
          {offer.category}
        </span>
        <div className="offer__chips">
          <span className="o-chip">
            <KalaiIcon name="user-group" size={16} aria-hidden />
            {offer.investorsCount}
          </span>
          <span className="o-chip o-chip--progress">
            {offer.raisedLabel}
            <span className="o-chip__bar">
              <span style={{ width: `${pct}%` }} />
            </span>
          </span>
          <span className="o-chip">
            <KalaiIcon name="money-dollar" size={16} aria-hidden />
            {ticket}
          </span>
        </div>
      </PortalNavLink>
      <div className="offer__body">
        <PortalNavLink href={offer.href} className="offer__text block no-underline">
          <h3 className="offer__title">{offer.title}</h3>
          <p className="offer__desc">{offer.subtitle || offer.description}</p>
        </PortalNavLink>
        {offer.isFunded ? (
          <div className="offer__ctas">
            <PortalNavLink href={offer.href} className="btn btn--primary offer__cta">
              View
            </PortalNavLink>
            <PortalNavLink href={withdrawHref} className="btn btn--secondary offer__cta">
              Withdraw
            </PortalNavLink>
          </div>
        ) : (
          <PortalNavLink href={investHref} className="btn btn--primary offer__cta">
            Invest
          </PortalNavLink>
        )}
      </div>
    </article>
  )
}

/** @deprecated Use PortalAdvisorBanner from @/components/portal/PortalAdvisorBanner */
export function PortalPlacerAdvisorBanner() {
  return <PortalAdvisorBanner />
}

type Props = {
  offers: PortalExclusiveOffer[]
  /** Coffres catalogue (`vault_simple`) — marketing Vault Builder + moteur vault plateforme. */
  vaultProducts?: PortalVaultProduct[]
  coffreBundles: PortalCryptoBundle[]
  panierBundles: PortalCryptoBundle[]
  defiVaults?: VaultUnion[]
  showDeFiVaults?: boolean
  /** Offres exclusives encore en chargement sans données affichables (shimmer dédié). */
  offersLoading?: boolean
  /** Coffres catalogue (`vault_simple`) encore en chargement (shimmer dédié). */
  vaultsLoading?: boolean
  /** Marchés (paniers / coffres bundle) encore en chargement sans données affichables. */
  marketsBundlesLoading?: boolean
  /** Vaults Morpho / Ledgity encore en chargement. */
  defiVaultsLoading?: boolean
}

export function PortalPlacerView({
  offers,
  vaultProducts = [],
  coffreBundles,
  panierBundles,
  defiVaults = [],
  showDeFiVaults = false,
  offersLoading = false,
  vaultsLoading = false,
  marketsBundlesLoading = false,
  defiVaultsLoading = false,
}: Props) {
  const router = useRouter()
  const [filter, setFilter] = useState<PlacerFilterId>('all')

  const openBundleInvest = (bundle: PortalCryptoBundle) => {
    const href = resolvePortalBundleFlowRoute(bundle, 'invest')
    if (href) router.push(href)
  }

  const show = (key: PlacerFilterId) => filter === 'all' || filter === key

  const bannerOffer =
    offers.find((o) => o.slug.toLowerCase().includes('niseko')) ?? offers[0] ?? null

  const coffreCards = [
    ...vaultProducts.map((vault) => ({
      key: `vault-product-${vault.id}`,
      kind: 'vault_product' as const,
      vault,
    })),
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
            if (isLedgityVault(vault)) {
              router.push(portalLedgityVaultInvestRoute(vault.id))
            } else {
              router.push(portalMorphoVaultInvestRoute(vault.vaultAddress))
            }
          },
          onWithdraw: () => {
            if (isLedgityVault(vault)) {
              router.push(portalLedgityVaultInvestRoute(vault.id, 'withdraw'))
            } else {
              router.push(portalMorphoVaultInvestRoute(vault.vaultAddress, 'withdraw'))
            }
          },
        }))
      : []),
  ]

  const showCoffresSection =
    show('coffres') &&
    (coffreCards.length > 0 ||
      vaultsLoading ||
      marketsBundlesLoading ||
      (showDeFiVaults && defiVaultsLoading))

  const showPaniersSection = show('paniers') && (panierBundles.length > 0 || marketsBundlesLoading)

  return (
    <>
      <div className="portal-placer-grid">
        <div className="col-main">
          <PortalPlacerBanner offer={bannerOffer} />
          <PortalPlacerFilter value={filter} onChange={setFilter} />

          {showCoffresSection ? (
            <div id="placer-coffres" className="placer-section">
              <PortalPlacerSectionHead
                title="Vaults"
                desc="A productive reserve, matched to your time horizon."
                action={
                  <PortalPlacerSeeAll href="#placer-coffres">View all vaults</PortalPlacerSeeAll>
                }
              />
              {coffreCards.length > 0 ? (
                <div className="placer-grid placer-grid--2">
                  {coffreCards.map((card) => {
                    if (card.kind === 'bundle') {
                      return (
                        <PortalPlacerBundleCoffreCard
                          key={card.key}
                          bundle={card.bundle}
                          onInvest={() => openBundleInvest(card.bundle)}
                        />
                      )
                    }
                    if (card.kind === 'vault_product') {
                      const vault = card.vault
                      return (
                        <PortalPlacerCoffreCard
                          key={card.key}
                          title={vault.title}
                          description={vault.subtitle || vault.description}
                          photo={resolveExclusiveOfferCoverUrl(vault.coverUrl, vault.slug)}
                          perf={vault.apyLabel.replace(' APR', '')}
                          liquidity={vault.raisedLabel}
                          currency={vault.assetSymbol ?? 'USDC'}
                          currencyIcon={resolveCurrencyIcon(vault.assetSymbol ?? 'USDC')}
                          categoryIcon="vault"
                          href={vault.href}
                          onInvest={() =>
                            router.push(resolvePortalVaultProductInvestRoute(vault))
                          }
                        />
                      )
                    }
                    const { key, kind: _kind, ...defiCard } = card
                    return <PortalPlacerCoffreCard key={key} {...defiCard} />
                  })}
                </div>
              ) : (
                <PortalPlacerSectionSkeleton />
              )}
            </div>
          ) : null}

          {show('offres') && (offers.length > 0 || offersLoading) ? (
            <div id="placer-offres" className="placer-section">
              <PortalPlacerSectionHead
                title="Exclusive offers"
                desc="A monthly selection of tokenized assets, vetted by our investment committee."
                action={
                  <PortalPlacerSeeAll href="#placer-offres">View all offers</PortalPlacerSeeAll>
                }
              />
              {offers.length > 0 ? (
                <div className="placer-grid placer-grid--2">
                  {offers.map((offer) => (
                    <PortalPlacerOfferCard key={offer.id} offer={offer} />
                  ))}
                </div>
              ) : (
                <PortalPlacerSectionSkeleton />
              )}
            </div>
          ) : null}

          {showPaniersSection ? (
            <div id="placer-paniers" className="placer-section">
              <PortalPlacerSectionHead
                title="Crypto baskets"
                desc="Thematic exposures rebalanced every month."
                action={
                  <PortalPlacerSeeAll href="#placer-paniers">View all baskets</PortalPlacerSeeAll>
                }
              />
              {panierBundles.length > 0 ? (
                <div className="placer-grid placer-grid--2">
                  {panierBundles.map((bundle) => (
                    <PortalPlacerBasketCard
                      key={bundle.id}
                      bundle={bundle}
                      onInvest={() => openBundleInvest(bundle)}
                    />
                  ))}
                </div>
              ) : (
                <PortalPlacerSectionSkeleton />
              )}
            </div>
          ) : null}
        </div>

        <aside className="col-side">
          <PortalPlacerAdvisorBanner />
        </aside>
      </div>
    </>
  )
}
