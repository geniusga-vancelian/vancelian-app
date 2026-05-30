'use client'

import { AppAccountDot } from './AppAccountDot'
import { AppBorrowCtaCard } from './AppBorrowCtaCard'
import { AppButton } from './AppButton'
import { AppLoanCard } from './AppLoanCard'
import { AppMobileStickyBar } from './AppMobileStickyBar'

/** Aperçu live des composants React Webapp-full (complète les iframes). */
export function AppDsShowcaseReactLive() {
  return (
    <section className="app-ds-sec" id="w-full-react">
      <header className="app-ds-sec__head">
        <span className="app-ds-sec__dot" aria-hidden />
        <span className="app-ds-sec__num">16b</span>
        <h2 className="app-ds-sec__title">Webapp-full — Composants React</h2>
        <span className="app-ds-sec__count">5 exports · live</span>
      </header>
      <div className="app-ds-grid flex flex-col gap-8">
        <article className="app-ds-item">
          <header className="app-ds-item__head">
            <h3 className="app-ds-item__title">AppAccountDot · safran / blue</h3>
          </header>
          <div className="rounded-v-card border border-v-fg-10 bg-v-bg p-6">
            <div className="flex flex-wrap gap-4">
              <AppAccountDot variant="safran" glyph="CR" />
              <AppAccountDot variant="blue" glyph="MP" />
              <AppAccountDot variant="green" glyph="EP" />
            </div>
          </div>
        </article>

        <article className="app-ds-item">
          <header className="app-ds-item__head">
            <h3 className="app-ds-item__title">AppBorrowCtaCard</h3>
          </header>
          <div className="max-w-xl">
            <AppBorrowCtaCard
              lead="Empruntez des USDC en garantissant vos cryptos — sans les vendre."
              ctaLabel="Demander une avance"
              onCtaClick={() => undefined}
            />
          </div>
        </article>

        <article className="app-ds-item">
          <header className="app-ds-item__head">
            <h3 className="app-ds-item__title">AppLoanCard</h3>
          </header>
          <div className="max-w-xl">
            <AppLoanCard
              assetTitle="Garantie Bitcoin"
              collateralSubtitle="0,42 cbBTC en garantie"
              collateralIconUrl="/app-ds/assets/crypto/btc.svg"
              safety="ok"
              safetyLabel="Sain"
              usagePercent={42}
              stats={[
                { label: 'Montant emprunté', value: '12 480,00 USDC' },
                {
                  label: "Taux d'intérêt",
                  value: '4,2 % variable',
                },
              ]}
              onClick={() => undefined}
            />
          </div>
        </article>

        <article className="app-ds-item">
          <header className="app-ds-item__head">
            <h3 className="app-ds-item__title">AppMobileStickyBar</h3>
          </header>
          <div className="relative overflow-hidden rounded-v-card border border-v-fg-10 bg-v-bg">
            <AppMobileStickyBar
              className="!relative !bottom-auto !block"
              figure="+ 7,2 %"
              figureTone="gain"
              subtitle="Sur 1 an"
            >
              <AppButton variant="primary">Investir</AppButton>
            </AppMobileStickyBar>
          </div>
        </article>
      </div>
    </section>
  )
}
