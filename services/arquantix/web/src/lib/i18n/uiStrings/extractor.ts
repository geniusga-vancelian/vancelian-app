import { ContentStatus, Prisma, type PrismaClient, TranslationStatus } from '@prisma/client'

import { inferNamespace, isValidUiKey } from './keyTaxonomy'
import type { ArbFile } from './arbReader'

/**
 * Extracteur ARB → table `cms_ui_strings`.
 *
 * **Contrat d'idempotence** :
 *   - L'extraction ne **crée jamais** de PUBLISHED. Le statut PUBLISHED reste
 *     contrôlé exclusivement par l'admin via le bouton "Publier".
 *   - Pour DRAFT, on `upsert` :
 *     - row absente            → `value = arbValue`, `sourceText = arbValueOfDefault`, `source = 'arb_extract'`.
 *     - row présente & `value` n'a jamais été customisée
 *       (`value === ancien sourceText`)               → MAJ `value`, `sourceText`, `description`, `placeholders`.
 *     - row présente & `value` customisée par admin   → MAJ uniquement `sourceText`, `description`, `placeholders`.
 *       L'override admin reste intact, mais il "voit" maintenant le nouveau
 *       texte source côté UI (diff dans la table admin).
 *
 * Cette politique est dans la lignée de Lokalise/Locize : le source change,
 * la traduction reste, le traducteur est notifié visuellement.
 */
export type ExtractArbStats = {
  /// Nombre total de keys parcourues (toutes locales).
  totalKeys: number
  /// Lignes créées en DB (DRAFT).
  created: number
  /// Lignes mises à jour avec MAJ de `value` (override admin absent).
  updatedFull: number
  /// Lignes mises à jour avec MAJ de metadata uniquement (override admin présent).
  updatedMetaOnly: number
  /// Keys ignorées car invalides (cf. `isValidUiKey` mode permissif).
  invalidKeys: string[]
}

/// Extrait toutes les entrées ARB et synchronise la DB.
export async function extractArbToDb(
  prisma: PrismaClient | Prisma.TransactionClient,
  arbs: ArbFile[],
  opts: {
    /// Locale source (defaultLocale du site) — utilisée pour `sourceText`.
    defaultLocale: string
    /// Origine technique de l'extraction (`arb_extract` par défaut, `lokalise_pull`
    /// pour le script Lokalise → DB).
    source?: string
    /// Si true (par défaut), refuse les keys non conformes à `isValidUiKey`.
    /// Sinon les keys non conformes sont **acceptées** mais classées dans
    /// le namespace `misc` (utile pour les keys ARB camelCase historiques).
    strictKeys?: boolean
  },
): Promise<ExtractArbStats> {
  const stats: ExtractArbStats = {
    totalKeys: 0,
    created: 0,
    updatedFull: 0,
    updatedMetaOnly: 0,
    invalidKeys: [],
  }
  const source = opts.source ?? 'arb_extract'
  const strict = opts.strictKeys ?? false

  /// Indexation par locale → keys (pour récupérer le sourceText efficacement).
  const byLocale = new Map<string, Map<string, ArbFile['entries'][number]>>()
  for (const arb of arbs) {
    const m = new Map<string, ArbFile['entries'][number]>()
    for (const e of arb.entries) m.set(e.key, e)
    byLocale.set(arb.locale, m)
  }
  const defaultMap = byLocale.get(opts.defaultLocale) ?? new Map()

  for (const arb of arbs) {
    for (const entry of arb.entries) {
      stats.totalKeys += 1
      const validForStrict = isValidUiKey(entry.key, { allowMisc: !strict })
      if (!validForStrict) {
        stats.invalidKeys.push(entry.key)
        if (strict) continue
      }
      const namespace = inferNamespace(entry.key)
      const sourceText = (defaultMap.get(entry.key)?.value ?? entry.value) || entry.value

      const existing = await prisma.cmsUiString.findUnique({
        where: {
          key_locale_status: {
            key: entry.key,
            locale: arb.locale,
            status: ContentStatus.DRAFT,
          },
        },
      })

      if (!existing) {
        await prisma.cmsUiString.create({
          data: {
            key: entry.key,
            namespace,
            locale: arb.locale,
            value: entry.value,
            sourceText,
            description: entry.description ?? null,
            placeholders: entry.placeholders
              ? (entry.placeholders as Prisma.InputJsonValue)
              : Prisma.JsonNull,
            status: ContentStatus.DRAFT,
            translationStatus:
              arb.locale === opts.defaultLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.MACHINE,
            source,
          },
        })
        stats.created += 1
        continue
      }

      const adminCustomized = existing.value !== (existing.sourceText ?? entry.value)
      if (adminCustomized) {
        /// Override admin : on ne touche pas à `value`, juste les metadata.
        await prisma.cmsUiString.update({
          where: { id: existing.id },
          data: {
            sourceText,
            description: entry.description ?? null,
            placeholders: entry.placeholders
              ? (entry.placeholders as Prisma.InputJsonValue)
              : Prisma.JsonNull,
            namespace,
          },
        })
        stats.updatedMetaOnly += 1
      } else {
        /// L'admin n'avait jamais customisé : on resync intégralement (value
        /// suit l'ARB, garantit que les nouvelles keys ARB se reflètent
        /// immédiatement même si extract relancé).
        await prisma.cmsUiString.update({
          where: { id: existing.id },
          data: {
            value: entry.value,
            sourceText,
            description: entry.description ?? null,
            placeholders: entry.placeholders
              ? (entry.placeholders as Prisma.InputJsonValue)
              : Prisma.JsonNull,
            namespace,
          },
        })
        stats.updatedFull += 1
      }
    }
  }

  return stats
}
