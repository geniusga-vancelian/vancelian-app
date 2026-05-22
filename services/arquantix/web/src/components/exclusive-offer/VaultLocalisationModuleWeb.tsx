'use client'

import { usePathname } from 'next/navigation'

import {
  SIMPLE_MARKDOWN_MODULE_TITLE_TYPO,
  VAULT_MODULE_DESCRIPTION_TYPO,
  VAULT_MODULE_MEDIA_FRAME_CLASS,
} from '@/components/design-system'
import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'
import { vaultCommonCta } from '@/lib/i18n/vaultCommonCta'
import {
  isGoogleMapsIframeEmbedUrl,
  normalizeGoogleMapsEmbedInput,
  preferGoogleMapsPinnedEmbedIframeSrc,
} from '@/lib/maps/resolveMapsShareLink'

type Props = {
  content: Record<string, unknown>
}

/**
 * Module Localisation (web public) : même logique de titre que [VaultVideoBlockArticle].
 * Pas de carte / encadrement autour du bloc — le fond blanc vient du parent (page offre).
 * Espacements 32px (h-8) entre titre / description / carte.
 */
export function VaultLocalisationModuleWeb({ content }: Props) {
  const pathname = usePathname() ?? ''
  const loc = getActiveLocaleFromPathname(pathname)
  const titleRaw = typeof content.moduleTitle === 'string' ? content.moduleTitle.trim() : ''
  const description = typeof content.description === 'string' ? content.description.trim() : ''
  const embedNorm = normalizeGoogleMapsEmbedInput(
    typeof content.embedUrl === 'string' ? content.embedUrl : '',
  )
  /** Pin rouge type Google : privilégie `q=lat,lng&output=embed` quand coords extrayables depuis `pb=` */
  const iframeSrc = preferGoogleMapsPinnedEmbedIframeSrc(embedNorm)

  const showMap = isGoogleMapsIframeEmbedUrl(embedNorm)
  const hasDesc = description.length > 0
  const showTitle = titleRaw.length > 0

  if (!showTitle && !hasDesc && !showMap && !embedNorm) {
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
      {showMap ? (
        <>
          {(hasDesc || (showTitle && !hasDesc)) ? <div className="h-8" aria-hidden /> : null}
          {/* ~80 % de la largeur utile (comme vidéo / image pleine largeur, −20 %) */}
          <div className="mx-auto w-4/5 min-w-0 max-w-full">
            <div className={VAULT_MODULE_MEDIA_FRAME_CLASS}>
              <iframe
                title={vaultCommonCta(loc, 'map')}
                src={iframeSrc}
                className="aspect-video w-full min-h-[220px] border-0 bg-v-fg-05"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                allowFullScreen
              />
            </div>
          </div>
        </>
      ) : embedNorm.length > 0 ? (
        <p className="mt-6 text-center font-ui text-[14px] text-v-error">
          {vaultCommonCta(loc, 'map_embed_invalid')}
        </p>
      ) : null}
    </div>
  )
}
