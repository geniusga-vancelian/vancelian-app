'use client'

import { usePathname } from 'next/navigation'

import {
  SIMPLE_MARKDOWN_MODULE_TITLE_TYPO,
  VAULT_MODULE_DESCRIPTION_TYPO,
} from '@/components/design-system'
import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'
import { vaultCommonCta } from '@/lib/i18n/vaultCommonCta'
import {
  isVirtualVisualizationEmbedUrl,
  normalizeVirtualVisualizationInput,
} from '@/lib/vault/normalizeVirtualVisualizationUrl'

type Props = {
  content: Record<string, unknown>
}

/**
 * Visite virtuelle (web public) : titre + description dans la colonne, iframe en breakout pleine largeur.
 */
export function VaultVirtualVisualizationModuleWeb({ content }: Props) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const titleRaw =
    typeof content.moduleTitle === 'string' ? content.moduleTitle.trim() : ''
  const description =
    typeof content.description === 'string' ? content.description.trim() : ''
  const urlNorm = normalizeVirtualVisualizationInput(
    typeof content.visualizationUrl === 'string' ? content.visualizationUrl : '',
  )

  const showFrame = isVirtualVisualizationEmbedUrl(urlNorm)
  const hasDesc = description.length > 0
  const showTitle = titleRaw.length > 0
  const rawUrl =
    typeof content.visualizationUrl === 'string' ? content.visualizationUrl.trim() : ''

  if (!showTitle && !hasDesc && !showFrame && !rawUrl) {
    return null
  }

  return (
    <div className="w-full">
      {showTitle ? <h2 className={SIMPLE_MARKDOWN_MODULE_TITLE_TYPO}>{titleRaw}</h2> : null}
      {showTitle && hasDesc ? <div className="h-8" aria-hidden /> : null}
      {hasDesc ? (
        <p className={`mx-auto max-w-3xl text-center ${VAULT_MODULE_DESCRIPTION_TYPO}`}>
          {description}
        </p>
      ) : null}
      {showFrame ? (
        <>
          {hasDesc || (showTitle && !hasDesc) ? <div className="h-8" aria-hidden /> : null}
          <div className="relative left-1/2 w-screen max-w-[100vw] -translate-x-1/2">
            <div className="overflow-hidden border-y border-neutral-200 bg-neutral-100 shadow-sm">
              <iframe
                title={vaultCommonCta(loc, 'virtual_tour')}
                src={urlNorm}
                className="block h-[min(85vh,920px)] w-full min-h-[480px] border-0"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                allowFullScreen
                allow="accelerometer; gyroscope; magnetometer; fullscreen; xr-spatial-tracking; autoplay; microphone; camera"
              />
            </div>
          </div>
        </>
      ) : rawUrl.length > 0 ? (
        <p className="mt-6 text-center text-sm text-amber-800">
          {vaultCommonCta(loc, 'virtual_tour_embed_invalid')}
        </p>
      ) : null}
    </div>
  )
}
