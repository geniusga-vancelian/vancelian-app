"use client";

/**
 * Wrapper CMS — rendu via design-system FAQ (layout 70/30 + aside sticky).
 */
import React from "react";
import FAQ from "@/components/design-system/FAQ";
import { Container } from "@/components/ui/Container";
import { parseEditorialTitle } from "@/lib/cms/parseEditorialTitle";

export interface FaqSectionProps {
  /** Surtitre / pastille au-dessus du titre (CMS, traduisible). */
  eyebrow?: string;
  /**
   * Titre canonique du module FAQ. Aligné sur la convention
   * Surtitre / Titre / Description des autres modules CMS.
   */
  title?: string;
  /**
   * Description optionnelle (chapô) affichée sous le titre.
   * Aucun rendu si vide — pas de fallback hardcodé.
   */
  description?: string;
  /**
   * @deprecated Champ legacy — ancien emplacement du grand titre.
   * Lu en fallback uniquement si `title` est vide pour préserver les
   * contenus existants. L'admin n'écrit plus ici.
   */
  subtitle?: string;
  items?: Array<{
    id: string;
    question: string;
    answerMarkdown: string;
  }>;
  support?: {
    title?: string;
    description?: string;
    ctaLabel?: string;
    ctaHref?: string;
    secondaryLinkLabel?: string;
    secondaryLinkHref?: string;
  };
  ui?: {
    expandAllLabel?: string;
    collapseAllLabel?: string;
  };
}

function mdToPlain(md: string) {
  return md
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)")
    .replace(/^#{1,6}\s+/gm, "")
    .trim();
}

export function FaqSection({
  eyebrow,
  title,
  description,
  subtitle,
  items = [],
  support,
  ui,
}: FaqSectionProps) {
  const mapped = items.map((item) => ({
    question: item.question,
    answer: mdToPlain(item.answerMarkdown || ""),
  }));

  const headlineRaw = title?.trim() || subtitle?.trim() || undefined;
  const headline = headlineRaw ? parseEditorialTitle(headlineRaw) : undefined;

  return (
    <div className="w-full bg-v-bg">
      <Container className="py-20 lg:py-24">
        <FAQ
          items={mapped}
          headline={headline}
          eyebrow={eyebrow}
          description={description}
          support={support}
          expandAllLabel={ui?.expandAllLabel}
          collapseAllLabel={ui?.collapseAllLabel}
        />
      </Container>
    </div>
  );
}
