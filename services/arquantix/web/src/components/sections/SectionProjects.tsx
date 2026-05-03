"use client";

/**
 * @deprecated Legacy ProjectCard grid replaced by design-system ProjetGallery; API stable for CMS.
 */
import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  buildLocalizedProjectDetailPath,
  buildLocalizedProjectHubPath,
  getActiveLocaleFromPathname,
  localizePublicInternalHref,
} from "@/lib/i18n/publicLocalizedRouting";
import ProjetGallery, {
  type Project,
} from "@/components/design-system/ProjetGallery/ProjetGallery";
import { Container } from "@/components/ui/Container";
import type { ProjectShrink } from "@/lib/cms/projects";
import {
  offerGalleryPhaseToImageLabel,
  type ProjectGalleryOfferPhase,
} from "@/lib/cms/galleryOfferPhase";
import { siteCommonCta } from "@/lib/i18n/siteCommonCta";

const OFFER_TAB_ALL = "all" as const;
type OfferTabId = typeof OFFER_TAB_ALL | ProjectGalleryOfferPhase;

type GalleryRow = {
  /** Identifiant stable (ex. packaged_product id ou slug legacy). */
  id?: string;
  title: string;
  location?: string;
  tags?: string[];
  description?: string;
  backgroundImage?: string;
  slug?: string;
  detailUrl?: string;
  fundedPct?: number;
  fundedText?: string;
  amountLine?: string;
  /** Phase offre (pool) → pastille image + onglets « toutes les offres ». */
  offerPhase?: ProjectGalleryOfferPhase | null;
};

/** Ordre aligné sur la maquette : toutes → en cours → à venir → clôturées.
 *  Les libellés sont localisés au moment du rendu via `siteCommonCta`. */
const OFFER_STATUS_TAB_IDS: OfferTabId[] = [
  OFFER_TAB_ALL,
  "in_progress",
  "upcoming",
  "delivered",
];

function offerStatusTabLabel(
  id: OfferTabId,
  locale: string | null | undefined,
): string {
  switch (id) {
    case "in_progress":
      return siteCommonCta(locale, "offer_status_in_progress");
    case "upcoming":
      return siteCommonCta(locale, "offer_status_upcoming");
    case "delivered":
      return siteCommonCta(locale, "offer_status_delivered");
    case OFFER_TAB_ALL:
    default:
      return siteCommonCta(locale, "offer_status_all");
  }
}

function rowMatchesOfferTab(row: GalleryRow, tab: OfferTabId): boolean {
  if (tab === OFFER_TAB_ALL) return true;
  return row.offerPhase === tab;
}

/** @deprecated Utiliser `@/lib/cms/projects` — réexport pour compat imports historiques. */
export type { ProjectShrink };

export interface SectionProjectsProps extends React.HTMLAttributes<HTMLElement> {
  /** Surtitre / ligne au-dessus du titre (CMS). */
  eyebrow?: string;
  title?: string;
  description?: string;
  items?: Array<{
    title: string;
    location?: string;
    tags?: string[];
    description?: string;
    mediaId?: string;
    mediaUrl?: string;
    backgroundImage?: string;
  }>;
  resolvedProjects?: ProjectShrink[];
  /** Si true (CMS), la grille liste déjà toutes les offres : masquer le CTA « Voir toutes les offres ». */
  showAllExclusiveOffers?: boolean;
  /** Libellé CTA « Voir toutes les offres » (CMS, traduisible). Fallback : `siteCommonCta(locale, 'view_all_offers')`. */
  viewAllButtonText?: string;
}

/** @deprecated Conservé pour compat ; la homepage utilise ProjetGallery. */
export interface ProjectCardProps {
  title: string;
  location?: string;
  tags?: string[];
  description?: string;
  backgroundImage?: string;
  className?: string;
  slug?: string;
}

/**
 * Tags Product Registry (admin) : entrées séparées ou une chaîne « A, B » ;
 * max 2 libellés pour la ligne au-dessus du titre.
 */
function normalizeCardInfoTags(tags: string[] | undefined): string[] {
  if (!tags?.length) return [];
  const out: string[] = [];
  for (const raw of tags) {
    const s = String(raw).trim();
    if (!s) continue;
    if (s.includes(",")) {
      out.push(...s.split(",").map((t) => t.trim()).filter(Boolean));
    } else {
      out.push(s);
    }
  }
  return out.slice(0, 2);
}

function mapToGalleryProjects(
  rows: GalleryRow[],
  pathLocale: ReturnType<typeof getActiveLocaleFromPathname>,
): Project[] {
  return rows.map((p, index) => {
    const infoTags = normalizeCardInfoTags(p.tags);
    const rawAmount = (p.amountLine ?? "").trim()
    const amount = rawAmount && rawAmount !== "—" ? rawAmount : ""
    const fallbackDetail =
      p.slug != null && p.slug !== ""
        ? buildLocalizedProjectDetailPath(pathLocale, p.slug)
        : undefined
    const rawDetail = typeof p.detailUrl === "string" ? p.detailUrl.trim() : ""
    const ctaLink = rawDetail
      ? localizePublicInternalHref(rawDetail, pathLocale)
      : fallbackDetail
    return {
      id: p.id || p.slug || `project-${index}`,
      image:
        p.backgroundImage ||
        "https://placehold.co/378x220/f3f3f3/62656e/png?text=Arquantix",
      imageStatusLabel: offerGalleryPhaseToImageLabel(p.offerPhase),
      infoTags,
      amount,
      title: p.title,
      description: p.description || "",
      fundedPercentage: p.fundedPct ?? 0,
      fundedText: p.fundedText ?? "—",
      ctaLink,
    }
  })
}

export function SectionProjects({
  eyebrow,
  title,
  description,
  items = [],
  resolvedProjects,
  showAllExclusiveOffers = false,
  viewAllButtonText,
  className,
  ...props
}: SectionProjectsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const pathLocale = getActiveLocaleFromPathname(pathname);
  const [offerTab, setOfferTab] = React.useState<OfferTabId>(OFFER_TAB_ALL);
  const resolvedTitle = title?.trim() || siteCommonCta(pathLocale, "projects_default_title");
  const resolvedViewAllLabel =
    viewAllButtonText?.trim() || siteCommonCta(pathLocale, "view_all_offers");

  let rows: GalleryRow[] = [];

  if (resolvedProjects && resolvedProjects.length > 0) {
    rows = resolvedProjects.map((p) => ({
      id: p.id,
      title: p.title,
      location: p.location || undefined,
      tags:
        p.cardTags && p.cardTags.length > 0
          ? p.cardTags
          : undefined,
      description: p.shortDescription || "",
      backgroundImage: p.coverUrl || undefined,
      slug: p.slug,
      detailUrl: p.detailUrl || undefined,
      fundedPct: p.fundingProgressPct ?? undefined,
      fundedText: p.fundingProgressLabel ?? undefined,
      amountLine: p.fundingAmountLine ?? undefined,
      offerPhase: p.galleryOfferPhase ?? null,
    }));
  } else if (items.length > 0) {
    rows = items;
  }

  const rowsForView =
    showAllExclusiveOffers && rows.length > 0
      ? rows.filter((r) => rowMatchesOfferTab(r, offerTab))
      : rows;

  const projects = mapToGalleryProjects(rowsForView, pathLocale);
  const sectionLabelText = eyebrow?.trim() ? eyebrow.trim() : undefined;

  const statusTabs =
    showAllExclusiveOffers && rows.length > 0
      ? OFFER_STATUS_TAB_IDS.map((id) => ({
          id,
          label: offerStatusTabLabel(id, pathLocale),
          isActive: id === offerTab,
        }))
      : [];

  return (
    <section
      id="projects"
      className={cn(
        "w-full bg-white pb-8 pt-0 md:pb-12",
        className,
      )}
      {...props}
    >
      <Container>
        <ProjetGallery
          sectionLabel={sectionLabelText}
          title={resolvedTitle}
          subtitle={description}
          tabs={statusTabs}
          projects={projects}
          viewAllButtonText={resolvedViewAllLabel}
          viewAllButtonLink={buildLocalizedProjectHubPath(pathLocale)}
          showViewAllButton={!showAllExclusiveOffers}
          onTabChange={(id) => setOfferTab(id as OfferTabId)}
          onProjectClick={(projectId) => {
            const row = rowsForView.find(
              (r, i) => (r.id || r.slug || `project-${i}`) === projectId,
            );
            if (row?.detailUrl?.trim()) {
              router.push(
                localizePublicInternalHref(row.detailUrl.trim(), pathLocale),
              );
              return;
            }
            const slug = row?.slug;
            if (slug) router.push(buildLocalizedProjectDetailPath(pathLocale, slug));
          }}
        />
        {rows.length === 0 ? (
          <p className="mx-auto mt-4 max-w-xl text-center text-sm text-neutral-500">
            {siteCommonCta(pathLocale, "no_offers_to_display")}
          </p>
        ) : null}
        {rows.length > 0 && projects.length === 0 && showAllExclusiveOffers ? (
          <p className="mx-auto mt-4 max-w-xl text-center text-sm text-muted-foreground">
            {siteCommonCta(pathLocale, "no_offers_in_category")}
          </p>
        ) : null}
      </Container>
    </section>
  );
}
