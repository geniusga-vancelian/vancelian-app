import * as React from 'react'
import { emailDsColors, emailDsFonts, emailDsType } from '@/email-ds/tokens'
import { EmailWordmark } from '@/email-ds/components/EmailWordmark'

export type EmailNavLink = { label: string; href: string }

export type EmailHeaderProps =
  | {
      level: 1
      /** URL absolue recommandée pour image hero (CDN / origine publique) */
      heroImageUrl: string
      eyebrow: string
      title: string
      kicker?: string
      viewInBrowserHref?: string
      viewInBrowserLabel?: string
      assetOrigin?: string
    }
  | {
      level: 2
      navLinks: EmailNavLink[]
      assetOrigin?: string
    }
  | {
      level: 3
      assetOrigin?: string
    }

/**
 * Niveaux d’en-tête e-mail (export Newsletter.zip) :
 * - L1 Hero : photo pleine largeur + scrim
 * - L2 Standard : wordmark + liens
 * - L3 Minimal : bandeau neutre centré
 */
export function EmailHeader(props: EmailHeaderProps) {
  const origin = props.assetOrigin

  if (props.level === 1) {
    const {
      heroImageUrl,
      eyebrow,
      title,
      kicker,
      viewInBrowserHref = '#',
      viewInBrowserLabel = 'View in browser',
    } = props
    return (
      <div
        style={{
          width: '100%',
          backgroundColor: emailDsColors.charcoal,
          backgroundImage: `linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.85) 100%), url('${heroImageUrl}')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          color: emailDsColors.white,
          padding: '32px 40px 56px',
          boxSizing: 'border-box',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 80,
          }}
        >
          <EmailWordmark heightPx={22} invert assetOrigin={origin} />
          <a
            href={viewInBrowserHref}
            style={{
              fontSize: 11,
              color: 'rgba(255,255,255,0.7)',
              fontFamily: emailDsFonts.eyebrow,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              textDecoration: 'none',
            }}
          >
            {viewInBrowserLabel}
          </a>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <span
            style={{
              fontSize: 11,
              color: 'rgba(255,255,255,0.85)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              fontFamily: emailDsFonts.eyebrow,
              padding: '3px 6px',
              border: '1px solid rgba(255,255,255,0.6)',
              borderRadius: 2,
              alignSelf: 'flex-start',
            }}
          >
            {eyebrow}
          </span>
          <h1
            style={{
              fontFamily: emailDsFonts.display,
              fontWeight: emailDsType.h1HeroEmail.fontWeight,
              fontSize: emailDsType.h1HeroEmail.fontSize,
              lineHeight: emailDsType.h1HeroEmail.lineHeight,
              letterSpacing: emailDsType.h1HeroEmail.letterSpacing,
              margin: 0,
              color: emailDsColors.white,
            }}
          >
            {title}
          </h1>
          {kicker ? (
            <div style={{ fontSize: emailDsType.body.fontSize, color: 'rgba(255,255,255,0.75)', marginTop: 4 }}>
              {kicker}
            </div>
          ) : null}
        </div>
      </div>
    )
  }

  if (props.level === 2) {
    const { navLinks } = props
    return (
      <div
        style={{
          background: emailDsColors.white,
          borderBottom: `1px solid ${emailDsColors.borderNavy20}`,
          padding: '20px 40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
          boxSizing: 'border-box',
        }}
      >
        <EmailWordmark heightPx={20} assetOrigin={origin} />
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          {navLinks.map((l) => (
            <a
              key={l.href + l.label}
              href={l.href}
              style={{
                fontSize: 13,
                color: emailDsColors.black,
                textDecoration: 'none',
                fontFamily: emailDsFonts.body,
              }}
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        background: emailDsColors.neutral100,
        padding: '20px 0',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        borderBottom: `1px solid ${emailDsColors.borderNavy20}`,
        boxSizing: 'border-box',
      }}
    >
      <EmailWordmark heightPx={18} assetOrigin={origin} />
    </div>
  )
}
