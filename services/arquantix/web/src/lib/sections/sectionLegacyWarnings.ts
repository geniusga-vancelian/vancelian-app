/**
 * Avertissements non bloquants pour l’admin : données legacy, alias ou champs
 * ignorés au rendu — affichés au-dessus de l’éditeur structuré.
 */

export type SectionLegacyWarningLevel = 'info' | 'warn'

export interface SectionLegacyWarning {
  readonly level: SectionLegacyWarningLevel
  /** Clé stable pour React / tests */
  readonly code: string
  readonly message: string
}

export function getSectionLegacyWarnings(
  canonicalKey: string,
  data: unknown,
): SectionLegacyWarning[] {
  const out: SectionLegacyWarning[] = []
  if (data == null || typeof data !== 'object' || Array.isArray(data)) {
    return out
  }
  const d = data as Record<string, unknown>

  switch (canonicalKey) {
    case 'faq': {
      const title = typeof d.title === 'string' ? d.title.trim() : ''
      const subtitle = typeof d.subtitle === 'string' ? d.subtitle.trim() : ''
      if (subtitle && !title) {
        out.push({
          level: 'info',
          code: 'faq_subtitle_fallback',
          message:
            'Le titre affiché sur le site provient encore du champ legacy `subtitle`. Renseignez le champ « Titre » pour aligner le contenu sur la convention actuelle.',
        })
      }
      break
    }
    case 'cta': {
      const primary =
        typeof d.primaryButtonText === 'string' ? d.primaryButtonText.trim() : ''
      const legacy = typeof d.ctaText === 'string' ? d.ctaText.trim() : ''
      if (!primary && legacy) {
        out.push({
          level: 'info',
          code: 'cta_ctaText_alias',
          message:
            'Le libellé du bouton principal est pris depuis `ctaText` (alias legacy). Utilisez « Bouton principal — texte » (`primaryButtonText`) pour plus de clarté.',
        })
      }
      break
    }
    case 'feature_grid': {
      const url = typeof d.imageUrl === 'string' ? d.imageUrl.trim() : ''
      const mid = typeof d.imageMediaId === 'string' ? d.imageMediaId.trim() : ''
      const murl = typeof d.imageMediaUrl === 'string' ? d.imageMediaUrl.trim() : ''
      if (url && !mid && !murl) {
        out.push({
          level: 'warn',
          code: 'feature_grid_imageUrl_only',
          message:
            'Une URL d’image brute (`imageUrl`) est utilisée sans média médiathèque. Préférez le sélecteur d’image pour la cohérence et la diffusion CDN.',
        })
      }
      break
    }
    case 'how_it_works': {
      if (d.surface === 'dark') {
        out.push({
          level: 'info',
          code: 'how_it_works_surface_ignored',
          message:
            'La valeur `surface: "dark"` est conservée en données mais le rendu public force un fond clair. Vous pouvez la retirer du JSON brut.',
        })
      }
      break
    }
    default:
      break
  }

  return out
}
