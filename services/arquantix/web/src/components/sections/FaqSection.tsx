"use client";

/**
 * @deprecated Accordéon maison ; rendu via design-system FAQ.
 */
import React from "react";
import FAQ from "@/components/design-system/FAQ";
import { Container } from "@/components/ui/Container";

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
  ui,
}: FaqSectionProps) {
  const mapped = items.map((item) => ({
    question: item.question,
    answer: mdToPlain(item.answerMarkdown || ""),
  }));

  // Compat douce : on lit `title` en priorité, fallback `subtitle` (legacy).
  // Si les deux sont vides, on ne rend pas de titre (cf. règle « pas de
  // fallback hardcodé côté site »).
  const headline = (title?.trim() || subtitle?.trim() || undefined);

  return (
    <div className="w-full bg-white">
      <Container className="py-8 md:py-12">
        <FAQ
          items={mapped}
          headline={headline}
          eyebrow={eyebrow}
          description={description}
          expandAllLabel={ui?.expandAllLabel}
          collapseAllLabel={ui?.collapseAllLabel}
        />
      </Container>
    </div>
  );
}
