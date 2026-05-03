import * as React from 'react'
import {
  EmailShell,
  EmailHeader,
  EmailFooter,
  EmailEyebrow,
  EmailSectionRule,
  EmailPrimaryButton,
  EmailSecondaryButton,
  emailDsColors,
  emailDsFonts,
  emailDsType,
  emailDsRadius,
} from '@/email-ds'

export type NewsletterExampleProps = {
  /**
   * Origine publique utilisée pour résoudre les assets (`public/email-ds/*`).
   * Pour un envoi réel, passer une URL absolue (ex. `https://www.arquantix.com`).
   * En preview interne (admin, /preview), on peut laisser undefined ⇒ chemins relatifs.
   */
  assetOrigin?: string
  /** URL image hero (absolue recommandée pour les clients mail) */
  heroImageUrl?: string
}

const DEFAULT_HERO =
  'https://images.unsplash.com/photo-1494949360228-4e9bde560065?auto=format&fit=crop&w=1600&q=80'

/**
 * Newsletter « Quarterly Letter » complète (header L1 + body éditorial + CTA + footer).
 * Assemble **toutes** les primitives du DS e-mail pour servir de référence de bout en bout.
 *
 * Mappage conceptuel sur `EmailModule` (cf. `prisma/schema.prisma`) :
 * - HEADER module  → `<EmailHeader level={1} …>` (hero + eyebrow + title)
 * - BODY STARTER   → 1er bloc éditorial + CTA primaire
 * - FOOTER module  → `<EmailFooter …>`
 */
export function NewsletterExample({
  assetOrigin,
  heroImageUrl = DEFAULT_HERO,
}: NewsletterExampleProps = {}) {
  return (
    <EmailShell>
      <EmailHeader
        level={1}
        heroImageUrl={heroImageUrl}
        eyebrow="Quarterly Letter"
        title="The new architecture of private assets."
        kicker="Q2 · 2026 · 6 min read"
        viewInBrowserHref="#"
        assetOrigin={assetOrigin}
      />

      {/* Bloc intro */}
      <div style={{ padding: '40px 40px 8px', fontFamily: emailDsFonts.body }}>
        <div style={{ marginBottom: 18 }}>
          <EmailEyebrow>Letter from the desk</EmailEyebrow>
        </div>
        <h2
          style={{
            fontFamily: emailDsFonts.display,
            fontSize: emailDsType.h2Section.fontSize,
            fontWeight: emailDsType.h2Section.fontWeight,
            lineHeight: emailDsType.h2Section.lineHeight,
            letterSpacing: emailDsType.h2Section.letterSpacing,
            margin: '0 0 16px',
            color: emailDsColors.ink,
          }}
        >
          Real assets, transparent rails.
        </h2>
        <p
          style={{
            fontSize: emailDsType.lead.fontSize,
            lineHeight: emailDsType.lead.lineHeight,
            color: emailDsColors.textMuted,
            margin: '0 0 20px',
          }}
        >
          This quarter, we crossed the threshold most allocators have been
          watching for years: premium real assets — structured, audited, held
          in regulated custody — finally trade with the clarity of code.
          Here’s where Arquantix stands today, and what we’re building next.
        </p>
        <p
          style={{
            fontSize: emailDsType.body.fontSize,
            lineHeight: emailDsType.body.lineHeight,
            color: emailDsColors.ink,
            margin: '0 0 28px',
          }}
        >
          Our Vault Builder now composes allocations across gold, emerging
          credit, private real estate and tokenized treasuries from a single
          subscription flow. Each position is mirrored on‑chain, reconciled
          nightly against the custodian ledger, and accessible to the client
          through one signed portfolio view — without ever touching a wallet.
        </p>
        <EmailPrimaryButton href="#">Read the letter</EmailPrimaryButton>
      </div>

      <div style={{ padding: '32px 40px 8px' }}>
        <EmailSectionRule />
      </div>

      {/* Grille 2 cartes highlights */}
      <div
        style={{
          padding: '24px 40px 8px',
          fontFamily: emailDsFonts.body,
          display: 'flex',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        {[
          {
            eyebrow: 'Vault · #017',
            title: 'Gold Backed Yield',
            body: 'Physical bullion in LBMA vaults, 4.6% target net yield, quarterly distributions.',
            cta: 'Explore vault',
          },
          {
            eyebrow: 'Exclusive Offer',
            title: 'Geneva Prime Residential',
            body: 'Co‑investment in a CHF 28M residential asset, 7‑year horizon, reserved allocation.',
            cta: 'See offer',
          },
        ].map((card) => (
          <div
            key={card.title}
            style={{
              flex: '1 1 240px',
              background: emailDsColors.neutral100,
              borderRadius: emailDsRadius.card,
              padding: 20,
              boxSizing: 'border-box',
              minWidth: 240,
            }}
          >
            <div style={{ marginBottom: 10 }}>
              <EmailEyebrow>{card.eyebrow}</EmailEyebrow>
            </div>
            <h3
              style={{
                fontFamily: emailDsFonts.display,
                fontSize: emailDsType.h3Card.fontSize,
                fontWeight: emailDsType.h3Card.fontWeight,
                lineHeight: emailDsType.h3Card.lineHeight,
                letterSpacing: emailDsType.h3Card.letterSpacing,
                margin: '0 0 10px',
                color: emailDsColors.ink,
              }}
            >
              {card.title}
            </h3>
            <p
              style={{
                fontSize: emailDsType.body.fontSize,
                lineHeight: emailDsType.body.lineHeight,
                color: emailDsColors.textMuted,
                margin: '0 0 16px',
              }}
            >
              {card.body}
            </p>
            <EmailSecondaryButton href="#">{card.cta}</EmailSecondaryButton>
          </div>
        ))}
      </div>

      <div style={{ padding: '32px 40px 8px' }}>
        <EmailSectionRule />
      </div>

      {/* Bloc sombre encart stratégique */}
      <div
        style={{
          margin: '24px 40px 8px',
          background: emailDsColors.charcoal,
          color: emailDsColors.white,
          borderRadius: emailDsRadius.card,
          padding: '28px 28px 32px',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ marginBottom: 14 }}>
          <EmailEyebrow variant="light">On‑chain Custody</EmailEyebrow>
        </div>
        <h3
          style={{
            fontFamily: emailDsFonts.display,
            fontSize: emailDsType.h3Card.fontSize,
            fontWeight: emailDsType.h3Card.fontWeight,
            lineHeight: emailDsType.h3Card.lineHeight,
            letterSpacing: emailDsType.h3Card.letterSpacing,
            margin: '0 0 12px',
            color: emailDsColors.white,
          }}
        >
          MiCA‑ready by design.
        </h3>
        <p
          style={{
            fontSize: emailDsType.body.fontSize,
            lineHeight: emailDsType.body.lineHeight,
            color: 'rgba(255,255,255,0.78)',
            margin: '0 0 20px',
          }}
        >
          Segregated cold storage, weekly reserve attestations and chain‑level
          traceability are now standard across every Arquantix vault.
        </p>
        <EmailPrimaryButton href="#" dark>
          Read the attestation
        </EmailPrimaryButton>
      </div>

      <div style={{ padding: '32px 40px 0' }}>
        <EmailSectionRule />
      </div>

      {/* Sign‑off */}
      <div style={{ padding: '28px 40px 40px', fontFamily: emailDsFonts.body }}>
        <p
          style={{
            fontSize: emailDsType.body.fontSize,
            lineHeight: emailDsType.body.lineHeight,
            color: emailDsColors.ink,
            margin: '0 0 6px',
          }}
        >
          Warmly,
        </p>
        <p
          style={{
            fontSize: emailDsType.body.fontSize,
            lineHeight: emailDsType.body.lineHeight,
            color: emailDsColors.ink,
            margin: 0,
            fontWeight: 600,
          }}
        >
          The Arquantix desk
        </p>
      </div>

      <EmailFooter assetOrigin={assetOrigin} />
    </EmailShell>
  )
}
