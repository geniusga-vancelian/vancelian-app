/** Parse et affichage des warnings preview bundle invest (format API structuré). */

import { displayBundleAssetSymbol } from '@/lib/portal/bundleFormat'

export type BundleInvestPreviewWarningFields = {
  kind: string
  asset?: string
  display?: string
  code?: string
  detail?: string
}

function decodeField(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

/** Parse ``kind|key=value|…`` (valeurs URL-encodées côté API). */
export function parseBundleInvestPreviewWarning(raw: string): BundleInvestPreviewWarningFields {
  const text = raw.trim()
  if (!text) return { kind: 'unknown', detail: '' }
  const segments = text.split('|')
  const kind = segments[0] ?? 'unknown'
  const out: BundleInvestPreviewWarningFields = { kind }
  for (const segment of segments.slice(1)) {
    const eq = segment.indexOf('=')
    if (eq <= 0) continue
    const key = segment.slice(0, eq).trim()
    const value = decodeField(segment.slice(eq + 1))
    if (key === 'asset') out.asset = value
    else if (key === 'display') out.display = value
    else if (key === 'code') out.code = value
    else if (key === 'detail') out.detail = value
  }
  return out
}

const LIFI_CODE_MESSAGES: Record<string, (fields: BundleInvestPreviewWarningFields) => string> = {
  'bundle.lifi.no_person_id': () =>
    'Wallet Privy requis pour estimer l’investissement — reconnectez-vous ou contactez le support.',
  'bundle.lifi.wallet_missing': (f) =>
    `Wallet Base introuvable${f.display ? ` (${f.display})` : ''}. Vérifiez votre compte Privy.`,
  'bundle.lifi.wallet_invalid': () => 'Adresse wallet Privy invalide.',
  'bundle.lifi.quote_failed': (f) =>
    `Cotation Li.FI indisponible${f.display ? ` pour ${f.display}` : ''}${
      f.detail ? ` : ${f.detail}` : ''
    }`,
}

function formatStructuredPreviewWarning(fields: BundleInvestPreviewWarningFields): string | null {
  if (fields.kind === 'lifi_preview_failed') {
    const mapped = fields.code ? LIFI_CODE_MESSAGES[fields.code] : undefined
    if (mapped) return mapped(fields)
    const label = fields.display ?? fields.asset ?? 'cet actif'
    return `Cotation Li.FI indisponible pour ${label}${fields.detail ? ` : ${fields.detail}` : ''}`
  }
  if (fields.kind === 'exchange_preview_failed') {
    const label =
      fields.display ??
      (fields.asset ? displayBundleAssetSymbol(fields.asset) : undefined) ??
      'cet actif'
    const detail = fields.detail ?? ''
    if (detail.includes('market_quote_stale')) {
      return `Prix marché expiré pour ${label} — le moteur Exchange legacy ne peut pas estimer ce leg.`
    }
    return `Estimation indisponible pour ${label}${detail ? ` : ${detail}` : ''}`
  }
  return null
}

/** Message utilisateur pour un warning preview (structuré ou legacy texte brut). */
export function formatBundleInvestPreviewWarning(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return 'Prévisualisation indisponible pour ce montant.'

  if (trimmed.includes('|')) {
    const structured = formatStructuredPreviewWarning(parseBundleInvestPreviewWarning(trimmed))
    if (structured) return structured
  }

  // Legacy: swap_preview_failed:CBBTC: …
  if (trimmed.startsWith('swap_preview_failed:')) {
    const rest = trimmed.slice('swap_preview_failed:'.length)
    const colon = rest.indexOf(':')
    const asset = colon >= 0 ? rest.slice(0, colon).trim() : rest.trim()
    const detail = colon >= 0 ? rest.slice(colon + 1).trim() : ''
    const display = displayBundleAssetSymbol(asset)
    return formatBundleInvestPreviewWarning(
      `exchange_preview_failed|asset=${encodeURIComponent(asset)}|display=${encodeURIComponent(display)}|code=exchange.preview_failed|detail=${encodeURIComponent(detail)}`,
    )
  }

  if (trimmed.includes('market_quote_stale')) {
    return 'Prix du marché expiré — impossible d’estimer l’allocation pour le moment.'
  }

  return trimmed
}

/** Agrège plusieurs warnings preview en un bloc lisible. */
export function formatBundleInvestPreviewWarnings(warnings: string[] | undefined): string | null {
  if (!warnings?.length) return null
  const lines = warnings.map(formatBundleInvestPreviewWarning).filter(Boolean)
  if (!lines.length) return null
  return lines.join('\n')
}
