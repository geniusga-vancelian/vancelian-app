import * as React from 'react'
import { emailDsColors, emailDsFonts } from '@/email-ds/tokens'
import { EmailWordmark } from '@/email-ds/components/EmailWordmark'

export type EmailFooterSocial = { label: string; href: string }

export type EmailFooterProps = {
  tagline?: string
  social?: EmailFooterSocial[]
  copyright?: string
  unsubscribeHref?: string
  preferencesHref?: string
  unsubscribeLabel?: string
  preferencesLabel?: string
  assetOrigin?: string
}

const defaultTagline =
  'Premium real assets, structured into transparent on‑chain vaults. Geneva · Singapore · Bali.'

const defaultSocial: EmailFooterSocial[] = [
  { label: 'LinkedIn', href: '#' },
  { label: 'X', href: '#' },
  { label: 'Telegram', href: '#' },
  { label: 'WhatsApp', href: '#' },
]

export function EmailFooter({
  tagline = defaultTagline,
  social = defaultSocial,
  copyright = `© ${new Date().getFullYear()} Arquantix SA. All rights reserved.`,
  unsubscribeHref = '#',
  preferencesHref = '#',
  unsubscribeLabel = 'Unsubscribe',
  preferencesLabel = 'Preferences',
  assetOrigin,
}: EmailFooterProps) {
  return (
    <div
      style={{
        background: emailDsColors.black,
        color: emailDsColors.white,
        padding: '40px 40px 28px',
        fontFamily: emailDsFonts.body,
        boxSizing: 'border-box',
      }}
    >
      <EmailWordmark heightPx={26} invert assetOrigin={assetOrigin} style={{ marginBottom: 20 }} />
      <p
        style={{
          fontSize: 12,
          lineHeight: 1.7,
          color: emailDsColors.textLight,
          margin: '0 0 24px',
          maxWidth: 380,
        }}
      >
        {tagline}
      </p>
      <div
        style={{
          display: 'flex',
          gap: 20,
          marginBottom: 24,
          paddingBottom: 24,
          borderBottom: `1px solid ${emailDsColors.borderWhite12}`,
          flexWrap: 'wrap',
        }}
      >
        {social.map((s) => (
          <a
            key={s.label + s.href}
            href={s.href}
            style={{
              fontSize: 12,
              color: emailDsColors.textLight,
              textDecoration: 'none',
            }}
          >
            {s.label}
          </a>
        ))}
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
          fontSize: 11,
          color: emailDsColors.textSubtle,
        }}
      >
        <span>{copyright}</span>
        <span>
          <a
            href={unsubscribeHref}
            style={{ color: emailDsColors.textSubtle, textDecoration: 'underline' }}
          >
            {unsubscribeLabel}
          </a>
          {' · '}
          <a
            href={preferencesHref}
            style={{ color: emailDsColors.textSubtle, textDecoration: 'underline' }}
          >
            {preferencesLabel}
          </a>
        </span>
      </div>
    </div>
  )
}
