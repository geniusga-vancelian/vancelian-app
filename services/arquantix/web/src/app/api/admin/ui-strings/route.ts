import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus, Prisma, TranslationStatus } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import {
  inferNamespace,
  isValidUiKey,
  UI_STRING_NAMESPACES,
  type UiStringNamespace,
} from '@/lib/i18n/uiStrings/keyTaxonomy'

/**
 * GET /api/admin/ui-strings?locale=…&namespace=…&q=…&status=draft|published&limit=200&offset=0
 *
 * Renvoie la liste paginée des keys du DRAFT (par défaut) avec :
 *  - `value`            : valeur courante de la locale demandée (override si présent, sinon ARB)
 *  - `sourceText`       : texte source (defaultLocale) — utile au traducteur
 *  - `defaultValue`     : valeur PUBLISHED actuelle pour la locale demandée (peut être null)
 *  - `translationStatus`: ORIGINAL | MACHINE | APPROVED
 *
 * Filtres :
 *  - `locale` (défaut = `defaultLocale` admin)
 *  - `namespace` (un de `UI_STRING_NAMESPACES`, ou `all`)
 *  - `q` : full-text simple sur `key` ou `value` (case-insensitive, contains)
 *  - `status` : DRAFT (défaut) ou PUBLISHED — le PATCH écrit toujours DRAFT
 *    et optionnellement PUBLISHED (cf. POST `/publish`).
 *
 * `meta.coverage` : pour chaque locale activée, nombre de keys avec une row
 * **non-default** (i.e. value !== sourceText) — proxy de "% traduit" affiché
 * dans la barre admin.
 */

const querySchema = z.object({
  locale: z.string().trim().optional(),
  namespace: z.string().trim().optional(),
  q: z.string().trim().optional(),
  status: z.enum(['draft', 'published']).optional(),
  limit: z.coerce.number().int().min(1).max(500).optional(),
  offset: z.coerce.number().int().min(0).optional(),
})

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const i18n = await getSiteI18nSettingsUncached()
    const params = querySchema.parse(
      Object.fromEntries(request.nextUrl.searchParams.entries()),
    )

    const requestedLocale = params.locale || i18n.defaultLocale
    const status = params.status === 'published' ? ContentStatus.PUBLISHED : ContentStatus.DRAFT
    const limit = params.limit ?? 200
    const offset = params.offset ?? 0

    /// Whitelist anti-injection sur le namespace (UNION strict avec la liste connue).
    const requestedNs = (params.namespace || '').toLowerCase()
    const namespaceFilter: UiStringNamespace | null =
      requestedNs && requestedNs !== 'all'
        ? ((UI_STRING_NAMESPACES as readonly string[]).includes(requestedNs)
            ? (requestedNs as UiStringNamespace)
            : null)
        : null
    if (params.namespace && !namespaceFilter && requestedNs !== 'all') {
      return NextResponse.json(
        { error: `Unknown namespace "${params.namespace}". Allowed: ${UI_STRING_NAMESPACES.join(', ')}, all.` },
        { status: 400 },
      )
    }

    const where: Prisma.CmsUiStringWhereInput = {
      locale: requestedLocale,
      status,
    }
    if (namespaceFilter) where.namespace = namespaceFilter
    if (params.q && params.q.length >= 2) {
      where.OR = [
        { key: { contains: params.q, mode: 'insensitive' } },
        { value: { contains: params.q, mode: 'insensitive' } },
      ]
    }

    const [items, total] = await Promise.all([
      prisma.cmsUiString.findMany({
        where,
        orderBy: [{ namespace: 'asc' }, { key: 'asc' }],
        take: limit,
        skip: offset,
      }),
      prisma.cmsUiString.count({ where }),
    ])

    /// Pour chaque item, on récupère la valeur PUBLISHED courante (si différente du DRAFT)
    /// dans une seule requête groupée (par key).
    const keys = items.map((it) => it.key)
    const published = keys.length
      ? await prisma.cmsUiString.findMany({
          where: {
            key: { in: keys },
            locale: requestedLocale,
            status: ContentStatus.PUBLISHED,
          },
          select: { key: true, value: true },
        })
      : []
    const publishedByKey = new Map(published.map((p) => [p.key, p.value]))

    /// Couverture : par locale activée, nombre de DRAFT keys avec value ≠ sourceText.
    /// Utilisé par l'indicateur de complétude UI ("fr: 87/142").
    const coverageRows = await prisma.$queryRaw<
      Array<{ locale: string; total: bigint; translated: bigint }>
    >(Prisma.sql`
      SELECT locale,
             COUNT(*)::bigint AS total,
             COUNT(*) FILTER (WHERE value <> COALESCE("sourceText", value))::bigint AS translated
      FROM cms_ui_strings
      WHERE status = 'DRAFT'
      GROUP BY locale
    `)

    return NextResponse.json({
      items: items.map((it) => ({
        id: it.id,
        key: it.key,
        namespace: it.namespace,
        locale: it.locale,
        value: it.value,
        sourceText: it.sourceText,
        publishedValue: publishedByKey.get(it.key) ?? null,
        description: it.description,
        placeholders: it.placeholders,
        status: it.status,
        translationStatus: it.translationStatus,
        source: it.source,
        updatedAt: it.updatedAt,
      })),
      meta: {
        requestedLocale,
        defaultLocale: i18n.defaultLocale,
        supportedLocales: i18n.supportedLocales,
        total,
        limit,
        offset,
        availableNamespaces: UI_STRING_NAMESPACES,
        coverage: coverageRows.map((r) => ({
          locale: r.locale,
          total: Number(r.total),
          translated: Number(r.translated),
        })),
      },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid query', issues: error.issues },
        { status: 400 },
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/ui-strings GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}

const patchEntrySchema = z.object({
  /// Soit `id` (row existante), soit `key` (création directe).
  id: z.string().min(1).optional(),
  key: z.string().min(1).optional(),
  value: z.string(),
  /// Optionnel : description ou translation status fournis par l'admin.
  translationStatus: z.enum(['ORIGINAL', 'MACHINE', 'APPROVED']).optional(),
})

const patchSchema = z.object({
  entries: z.array(patchEntrySchema).min(1).max(500),
})

/**
 * PATCH /api/admin/ui-strings?locale=…&status=draft|published
 *
 * Upsert batch. Par défaut écrit DRAFT pour la locale demandée. Si
 * `status=published`, on copie également la valeur en PUBLISHED ("Publier"
 * = synchroniser DRAFT → PUBLISHED, idempotent).
 *
 * Garde-fous :
 *  - locale doit appartenir à `supportedLocales` (sauf si `multilingualEnabled=false`).
 *  - chaque entrée fournit soit `id`, soit `key` (création), pas les deux.
 *  - keys nouvelles : doivent passer `isValidUiKey(allowMisc=true)`.
 */
export async function PATCH(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale
    const writeScope =
      request.nextUrl.searchParams.get('status') === 'published' ? 'published' : 'draft'

    if (
      i18n.multilingualEnabled &&
      !(i18n.supportedLocales as readonly string[]).includes(requestedLocale)
    ) {
      return NextResponse.json(
        { error: `Locale "${requestedLocale}" not enabled` },
        { status: 400 },
      )
    }

    const body = patchSchema.parse(await request.json())

    const result = await prisma.$transaction(async (tx) => {
      let touched = 0
      let publishedCopied = 0
      for (const entry of body.entries) {
        if (!entry.id && !entry.key) {
          throw new Error('Entry must have either `id` or `key`.')
        }

        let row = entry.id
          ? await tx.cmsUiString.findUnique({ where: { id: entry.id } })
          : null
        if (!row && entry.key) {
          row = await tx.cmsUiString.findUnique({
            where: {
              key_locale_status: {
                key: entry.key,
                locale: requestedLocale,
                status: ContentStatus.DRAFT,
              },
            },
          })
        }

        if (!row) {
          /// Création (key custom de l'admin).
          if (!entry.key) throw new Error('Missing key for new entry.')
          if (!isValidUiKey(entry.key, { allowMisc: true })) {
            throw new Error(`Invalid key "${entry.key}".`)
          }
          row = await tx.cmsUiString.create({
            data: {
              key: entry.key,
              namespace: inferNamespace(entry.key),
              locale: requestedLocale,
              value: entry.value,
              sourceText: entry.value,
              status: ContentStatus.DRAFT,
              source: 'manual',
              translationStatus:
                entry.translationStatus ??
                (requestedLocale === i18n.defaultLocale
                  ? TranslationStatus.ORIGINAL
                  : TranslationStatus.APPROVED),
              updatedByUserId: session.userId,
            },
          })
          touched += 1
        } else {
          await tx.cmsUiString.update({
            where: { id: row.id },
            data: {
              value: entry.value,
              translationStatus:
                entry.translationStatus ??
                (requestedLocale === i18n.defaultLocale
                  ? TranslationStatus.ORIGINAL
                  : row.translationStatus === TranslationStatus.ORIGINAL
                    ? TranslationStatus.APPROVED
                    : row.translationStatus),
              updatedByUserId: session.userId,
            },
          })
          touched += 1
        }

        if (writeScope === 'published') {
          /// Synchronise la valeur publiée. Upsert sur (key, locale, PUBLISHED).
          await tx.cmsUiString.upsert({
            where: {
              key_locale_status: {
                key: row.key,
                locale: requestedLocale,
                status: ContentStatus.PUBLISHED,
              },
            },
            create: {
              key: row.key,
              namespace: row.namespace,
              locale: requestedLocale,
              value: entry.value,
              sourceText: row.sourceText,
              description: row.description,
              placeholders: row.placeholders ?? Prisma.JsonNull,
              status: ContentStatus.PUBLISHED,
              source: 'admin_publish',
              translationStatus:
                entry.translationStatus ??
                (requestedLocale === i18n.defaultLocale
                  ? TranslationStatus.ORIGINAL
                  : TranslationStatus.APPROVED),
              updatedByUserId: session.userId,
            },
            update: {
              value: entry.value,
              sourceText: row.sourceText,
              description: row.description,
              placeholders: row.placeholders ?? Prisma.JsonNull,
              translationStatus:
                entry.translationStatus ??
                (requestedLocale === i18n.defaultLocale
                  ? TranslationStatus.ORIGINAL
                  : TranslationStatus.APPROVED),
              updatedByUserId: session.userId,
            },
          })
          publishedCopied += 1
        }
      }
      return { touched, publishedCopied }
    })

    return NextResponse.json({
      success: true,
      meta: { requestedLocale, writeScope, ...result },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid payload', issues: error.issues },
        { status: 400 },
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/ui-strings PATCH]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
