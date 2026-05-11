/**
 * Résolution des cartes « Projects » CMS à partir des PackagedProduct EXCLUSIVE_OFFER (Vault Builder).
 */
import {
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'
import { Decimal } from '@prisma/client/runtime/library'

import { resolveVaultPresentation } from '@/lib/catalog/packagedCatalogHelpers'
import { getLocaleOrDefault } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import { localizedExclusiveOfferDetailPath } from '@/lib/i18n/localizedExclusiveOfferPath'

import type { ProjectGalleryOfferPhase } from './galleryOfferPhase'
import type { ProjectShrink } from './projects'

function fmtEur(d: Decimal | null | undefined): string {
  if (d == null) return '—'
  const n = Number(d)
  if (!Number.isFinite(n)) return '—'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(n)
}

function fundingPct(raised: Decimal | null | undefined, target: Decimal | null | undefined): number {
  if (raised == null || target == null) return 0
  const t = Number(target)
  const r = Number(raised)
  if (!Number.isFinite(t) || t <= 0 || !Number.isFinite(r)) return 0
  return Math.min(100, Math.round((r / t) * 100))
}

type LppFundingFields = {
  currentRaised: Decimal | null
  targetSize: Decimal
  status: string
  startDate: Date | null
}

/**
 * Statut grille : pas de pool / brouillon / lancement futur → à venir ;
 * financement partiel → en cours ; objectif atteint → clôturé (livrée financièrement).
 */
function deriveGalleryOfferPhase(lpp: LppFundingFields | null): ProjectGalleryOfferPhase {
  if (!lpp) return 'upcoming'
  const t = Number(lpp.targetSize)
  const r = Number(lpp.currentRaised ?? 0)
  if (Number.isFinite(t) && t > 0 && Number.isFinite(r) && r / t >= 0.999) {
    return 'delivered'
  }
  const pct = fundingPct(lpp.currentRaised, lpp.targetSize)
  if (pct >= 100) return 'delivered'

  const st = (lpp.status || '').toLowerCase()
  if (st === 'draft' && pct === 0) return 'upcoming'
  if (lpp.startDate && lpp.startDate.getTime() > Date.now()) return 'upcoming'

  return 'in_progress'
}

/** UUID v4 (packaged_products.id côté Postgres). */
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

/**
 * Le CMS stocke en principe `packaged_products.id` (UUID). Tolère les slugs (`eo-…`) si la donnée
 * a été copiée ou migrée à la main.
 */
async function mapExclusiveOfferRefsToUuids(orderedIds: string[]): Promise<string[]> {
  const slugSet = new Set<string>()
  for (const raw of orderedIds) {
    const t = (raw ?? '').trim()
    if (t && !UUID_RE.test(t)) slugSet.add(t)
  }

  let slugMap = new Map<string, string>()
  if (slugSet.size > 0) {
    const bySlug = await prisma.packagedProduct.findMany({
      where: {
        slug: { in: [...slugSet] },
        productType: PackagedProductType.EXCLUSIVE_OFFER,
      },
      select: { id: true, slug: true },
    })
    slugMap = new Map(bySlug.map((r) => [r.slug, r.id]))
  }

  const result: string[] = []
  for (const raw of orderedIds) {
    const t = (raw ?? '').trim()
    if (!t) continue
    if (UUID_RE.test(t)) {
      result.push(t)
      continue
    }
    const id = slugMap.get(t)
    if (id) result.push(id)
  }
  return result
}

const devShowDraftExclusiveOffers =
  process.env.NODE_ENV === 'development' &&
  process.env.ARQUANTIX_DEV_SHOW_DRAFT_EXCLUSIVE_OFFERS === 'true'

/**
 * Filtre `commercial_status` pour la grille / cartes EO.
 *
 * - **Production** : `PUBLISHED` uniquement (comportement site public).
 * - **`next dev`** : `PUBLISHED` + `DRAFT` — aligné sur le détail vault en local (sinon la page Projects
 *   reste vide tant que l’offre n’est pas passée « Publié » dans le registre, alors qu’elle est déjà
 *   éditable / visible en preview).
 * - Variable historique `ARQUANTIX_DEV_SHOW_DRAFT_EXCLUSIVE_OFFERS` : redondante en dev depuis l’alignement ci-dessus.
 */
export function galleryExclusiveOfferCommercialStatuses():
  | PackagedCommercialStatus
  | { in: PackagedCommercialStatus[] } {
  const includeDraft =
    process.env.NODE_ENV === 'development' || devShowDraftExclusiveOffers
  return includeDraft
    ? { in: [PackagedCommercialStatus.PUBLISHED, PackagedCommercialStatus.DRAFT] }
    : PackagedCommercialStatus.PUBLISHED
}

/**
 * Cartes galerie homepage à partir d’IDs `packaged_products.id` (ordre conservé).
 * Filtre : visibilité PUBLIC ; statut commercial selon {@link galleryExclusiveOfferCommercialStatuses}.
 */
export async function getExclusiveOfferCardsByPackagedProductIds(
  orderedIds: string[],
  locale: string,
): Promise<ProjectShrink[]> {
  if (orderedIds.length === 0) return []

  const resolvedLocale = getLocaleOrDefault(locale)
  const uuidOrdered = await mapExclusiveOfferRefsToUuids(orderedIds)
  if (uuidOrdered.length === 0) return []

  const rows = await prisma.packagedProduct.findMany({
    where: {
      id: { in: uuidOrdered },
      productType: PackagedProductType.EXCLUSIVE_OFFER,
      commercialStatus: galleryExclusiveOfferCommercialStatuses(),
      visibility: PackagedVisibility.PUBLIC,
    },
    include: {
      lendingPoolProduct: {
        select: {
          currentRaised: true,
          targetSize: true,
          status: true,
          startDate: true,
        },
      },
    },
  })

  const byId = new Map(rows.map((r) => [r.id, r]))
  const ordered = uuidOrdered.map((id) => byId.get(id)).filter((r): r is (typeof rows)[0] => r != null)

  if (
    process.env.NODE_ENV === 'development' &&
    ordered.length < uuidOrdered.length &&
    orderedIds.some((x) => (x ?? '').trim().length > 0)
  ) {
    console.warn(
      '[exclusiveOfferGallery] Certaines offres sélectionnées ne sont pas affichées (visibilité ≠ PUBLIC, statut commercial exclu en prod, ARCHIVED, ou ID/slug inconnu).',
    )
  }

  const cards: ProjectShrink[] = await Promise.all(
    ordered.map(async (pp) => {
      const pres = await resolveVaultPresentation({
        prisma,
        pageId: pp.pageId,
        locale: resolvedLocale,
      })

      const page = await prisma.page.findUnique({
        where: { id: pp.pageId },
        select: { slug: true, urlPath: true },
      })

      const lpp = pp.lendingPoolProduct
      const galleryOfferPhase = deriveGalleryOfferPhase(
        lpp
          ? {
              currentRaised: lpp.currentRaised,
              targetSize: lpp.targetSize,
              status: lpp.status,
              startDate: lpp.startDate,
            }
          : null,
      )
      const pct = fundingPct(lpp?.currentRaised ?? null, lpp?.targetSize ?? null)
      const target = lpp?.targetSize
      /** Carte : montant total à lever uniquement (pas de « courant / objectif »). */
      let fundingAmountLine: string | null = null
      if (target != null && Number(target) > 0) {
        fundingAmountLine = fmtEur(target)
      }

      const cardTags = Array.isArray(pp.tags)
        ? (pp.tags as unknown[]).filter((t): t is string => typeof t === 'string').slice(0, 2)
        : []

      const locationLine = pp.categorySlug
        ? pp.categorySlug.replace(/-/g, ' ')
        : 'Exclusive offer'

      const title = pres.title.trim() || page?.slug || pp.slug
      const shortDesc = pres.subtitle?.trim() || null
      const publicSlug = page?.slug ?? pp.slug
      /** Lien public localisé : `/[locale]/projects/[slug]` (cohérent avec la page hub `/[locale]/projects`). */
      const detailUrl = publicSlug
        ? localizedExclusiveOfferDetailPath(getLocaleOrDefault(locale), publicSlug)
        : null

      return {
        id: pp.id,
        slug: publicSlug,
        title,
        location: locationLine,
        shortDescription: shortDesc,
        description: shortDesc,
        descriptionLinks: null,
        howItWorks: null,
        keyInformation: null,
        faq: null,
        coverUrl: pres.coverUrl,
        coverAlt: title,
        investmentCategory: pp.categorySlug ?? null,
        teaserVideoUrl: null,
        hasGallery: false,
        competitiveAdvantages: null,
        detailUrl,
        cardTags: cardTags.length > 0 ? cardTags : null,
        fundingProgressPct: lpp ? pct : null,
        fundingProgressLabel: lpp ? `${pct}%` : null,
        fundingAmountLine: lpp ? fundingAmountLine : null,
        galleryOfferPhase,
      }
    }),
  )

  return cards
}

/**
 * Offres exclusives visibles sur le site (PUBLIC + statut commercial selon l’environnement),
 * les plus récentes en premier (`updatedAt` desc), puis cartes dans le même ordre.
 */
export async function getExclusiveOfferCardsNewestFirst(
  locale: string,
  limit: number,
): Promise<ProjectShrink[]> {
  const cap = Math.min(20, Math.max(1, Math.floor(limit)))
  const rows = await prisma.packagedProduct.findMany({
    where: {
      productType: PackagedProductType.EXCLUSIVE_OFFER,
      commercialStatus: galleryExclusiveOfferCommercialStatuses(),
      visibility: PackagedVisibility.PUBLIC,
    },
    orderBy: { updatedAt: 'desc' },
    take: cap,
    select: { id: true },
  })
  const ids = rows.map((r) => r.id)
  return getExclusiveOfferCardsByPackagedProductIds(ids, locale)
}
