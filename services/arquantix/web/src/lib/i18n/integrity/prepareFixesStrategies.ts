/**
 * Règles Lot 2 — choix de source et stratégie (documenté, prudent).
 *
 * Ordre des sources (MISSING) : `defaultLocale` d’abord, puis les autres locales ≠ cible
 * (`supportedLocales` dans `config/locales`).
 *
 * - MISSING : première source non vide ; si `classify(source) === OK` pour la cible → copy-as-is,
 *   sinon → translate-from-source (provider, souvent mock en lot 2).
 * - WRONG_LANGUAGE : si le brouillon `defaultLocale` pour le même champ est OK pour la cible → copy-as-is ;
 *   sinon si `detectedLocale` est défini → translate-from-source sur le texte **actuel** (locale source = détectée) ;
 *   sinon → needs-review.
 * - MIXED_LANGUAGE : needs-review (pas de correction auto agressive).
 * - NEEDS_REVIEW : needs-review (pas de proposition automatique agressive ; pas de « magie »).
 * - NON_TRANSLATABLE : skip.
 */

import { defaultLocale, supportedLocales, type Locale } from '@/config/locales'

import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import { excerpt } from '@/lib/i18n/integrity/textPrep'
import type { TranslationProvider } from '@/lib/i18n/integrity/translationProvider'
import { getStringAtLot1Path } from '@/lib/i18n/integrity/fieldPathAccess'
import { stableFindingId } from '@/lib/i18n/integrity/findingId'
import type {
  CorrectionProposal,
  LinguisticAuditFinding,
} from '@/lib/i18n/integrity/types'

/** Locales sources candidates (brouillons), la locale par défaut du site en premier. */
export function sourceLocaleOrder(targetLocale: Locale): Locale[] {
  const withoutTarget = supportedLocales.filter((l) => l !== targetLocale)
  const def = defaultLocale as Locale
  if (!withoutTarget.includes(def)) return [...withoutTarget]
  return [def, ...withoutTarget.filter((l) => l !== def)]
}

function proposalId(findingId: string, strategy: CorrectionProposal['strategy']): string {
  return `prep-${stableFindingId([findingId, strategy])}`
}

function baseFields(f: LinguisticAuditFinding): Pick<
  CorrectionProposal,
  'findingId' | 'pageSlug' | 'domain' | 'fieldPath' | 'auditStatus'
> {
  return {
    findingId: f.id,
    pageSlug: f.pageSlug,
    domain: f.domain,
    fieldPath: f.fieldPath,
    auditStatus: f.status,
  }
}

/**
 * Construit une proposition pour un finding ≠ OK. Aucune écriture DB.
 */
export async function buildCorrectionProposal(
  f: LinguisticAuditFinding,
  draftByLocale: Map<Locale, unknown> | undefined,
  targetLocale: Locale,
  provider: TranslationProvider,
): Promise<CorrectionProposal> {
  const base = baseFields(f)
  const targetData = draftByLocale?.get(targetLocale)
  const currentText =
    targetData != null ? getStringAtLot1Path(targetData, f.domain, f.fieldPath) ?? '' : ''

  if (f.status === 'NON_TRANSLATABLE') {
    return {
      ...base,
      id: proposalId(f.id, 'skip'),
      strategy: 'skip',
      currentText,
      confidence: 0.2,
      recommendedAction: 'Aucune action automatique — champ marqué non traduisible.',
      rationale: 'Statut NON_TRANSLATABLE — hors correction auto (lot 2).',
    }
  }

  if (f.status === 'MIXED_LANGUAGE') {
    return {
      ...base,
      id: proposalId(f.id, 'needs-review'),
      strategy: 'needs-review',
      currentText,
      confidence: 0.35,
      recommendedAction: 'Revue manuelle : découper ou réécrire le bloc dans une seule langue.',
      rationale:
        'Mélange de langues détecté — pas de proposition automatique fiable (politique lot 2).',
    }
  }

  if (f.status === 'NEEDS_REVIEW') {
    return {
      ...base,
      id: proposalId(f.id, 'needs-review'),
      strategy: 'needs-review',
      currentText,
      confidence: 0.3,
      recommendedAction: 'Vérifier la langue et le contenu à la main avant tout apply futur.',
      rationale:
        'Texte ambigu, trop court ou indéterminé — pas de correction automatique agressive.',
    }
  }

  if (f.status === 'MISSING') {
    for (const loc of sourceLocaleOrder(targetLocale)) {
      const data = draftByLocale?.get(loc)
      const raw = data != null ? getStringAtLot1Path(data, f.domain, f.fieldPath) : undefined
      const src = typeof raw === 'string' ? raw.trim() : ''
      if (!src) continue

      const cls = classifyTextForTargetLocale(src, targetLocale)
      if (cls.status === 'OK') {
        return {
          ...base,
          id: proposalId(f.id, 'copy-as-is'),
          strategy: 'copy-as-is',
          sourceLocale: loc,
          sourceTextExcerpt: excerpt(src),
          currentText,
          proposedText: src,
          confidence: 0.82,
          recommendedAction:
            'Relecture rapide : le texte source semble déjà adapté à la locale cible ; copie telle quelle possible au apply.',
          rationale: `Source locale « ${loc} » (défaut en premier) : classification OK pour ${targetLocale}.`,
        }
      }

      const proposedText = await provider.translate(src, loc, targetLocale)
      return {
        ...base,
        id: proposalId(f.id, 'translate-from-source'),
        strategy: 'translate-from-source',
        sourceLocale: loc,
        sourceTextExcerpt: excerpt(src),
        currentText,
        proposedText,
        confidence: 0.48,
        recommendedAction:
          'Relecture obligatoire : aperçu produit par le provider mock (lot 2) ou futur moteur de traduction.',
        rationale: `Champ vide en cible — proposition à partir de la locale « ${loc} » (traduction simulée si locales différentes).`,
      }
    }

    return {
      ...base,
      id: proposalId(f.id, 'skip'),
      strategy: 'skip',
      currentText,
      confidence: 0.15,
      recommendedAction: 'Rédiger manuellement ou compléter une autre locale source d’abord.',
      rationale: 'Aucun texte source trouvé dans les brouillons des autres locales pour ce champ.',
    }
  }

  if (f.status === 'WRONG_LANGUAGE') {
    const defLoc = defaultLocale as Locale
    const defData = draftByLocale?.get(defLoc)
    const defRaw =
      defData != null ? getStringAtLot1Path(defData, f.domain, f.fieldPath) : undefined
    const defText = typeof defRaw === 'string' ? defRaw.trim() : ''

    if (defText) {
      const cls = classifyTextForTargetLocale(defText, targetLocale)
      if (cls.status === 'OK') {
        return {
          ...base,
          id: proposalId(f.id, 'copy-as-is'),
          strategy: 'copy-as-is',
          sourceLocale: defLoc,
          sourceTextExcerpt: excerpt(defText),
          currentText,
          proposedText: defText,
          confidence: 0.78,
          recommendedAction:
            'Relecture : le brouillon langue par défaut semble déjà conforme à la cible — remplacement possible au apply.',
          rationale: `Alignement sur le brouillon ${defLoc} (même champ), jugé OK pour ${targetLocale}.`,
        }
      }
    }

    if (f.detectedLocale && f.detectedLocale !== targetLocale && currentText.trim()) {
      const proposedText = await provider.translate(currentText, f.detectedLocale, targetLocale)
      return {
        ...base,
        id: proposalId(f.id, 'translate-from-source'),
        strategy: 'translate-from-source',
        sourceLocale: f.detectedLocale,
        sourceTextExcerpt: excerpt(currentText),
        currentText,
        proposedText,
        confidence: 0.52,
        recommendedAction:
          'Relecture : proposition basée sur la langue détectée du texte actuel (aperçu mock en lot 2).',
        rationale: `Traduction simulée ${f.detectedLocale} → ${targetLocale} à partir du contenu actuel du brouillon cible.`,
      }
    }

    return {
      ...base,
      id: proposalId(f.id, 'needs-review'),
      strategy: 'needs-review',
      currentText,
      confidence: 0.28,
      recommendedAction: 'Corriger manuellement ou choisir une source après revue.',
      rationale:
        'Langue incorrecte mais pas de source default OK ni locale détectée exploitable — revue manuelle.',
    }
  }

  return {
    ...base,
    id: proposalId(f.id, 'skip'),
    strategy: 'skip',
    currentText,
    confidence: 0.1,
    recommendedAction: 'Aucune règle lot 2 — traiter manuellement.',
    rationale: 'Statut d’audit non géré par le lot 2.',
  }
}
