"use client";

import type { HTMLAttributes } from "react";
import HowItWorks from "@/components/design-system/HowItWorks";
import { Container } from "@/components/ui/Container";
import { cn } from "@/lib/utils";

export interface SectionHowItWorksCmsProps extends HTMLAttributes<HTMLElement> {
  label?: string;
  title?: string;
  subtitle?: string;
  /** Masque 01, 02… sur les cartes lorsque true. */
  hideStepNumbering?: boolean;
  steps?: Array<{
    number: string
    title: string
    description: string
    imageMediaUrl?: string
    imageMediaAlt?: string | null
    stepButtonLabel?: string
    stepButtonHref?: string
  }>
  primaryCtaText?: string;
  primaryCtaHref?: string;
  secondaryCtaText?: string;
  secondaryCtaHref?: string;
  surface?: "light" | "dark";
}

/**
 * Bloc « How it works » piloté par le CMS (données JSON section `how_it_works`).
 */
export function SectionHowItWorksCms({
  label,
  title,
  subtitle,
  hideStepNumbering,
  steps,
  primaryCtaText,
  primaryCtaHref,
  secondaryCtaText,
  secondaryCtaHref,
  surface: _surface = "light",
  className,
  ...rest
}: SectionHowItWorksCmsProps) {
  /* Bloc marketing home : fond blanc uniquement (ignore anciennes valeurs CMS `surface: dark`). */
  return (
    <section className={cn("w-full bg-white", className)} {...rest}>
      <Container>
        <HowItWorks
          label={label}
          title={title}
          subtitle={subtitle}
          hideStepNumbering={hideStepNumbering === true}
          steps={steps && steps.length > 0 ? steps : undefined}
          surface="light"
          primaryCta={
            primaryCtaText
              ? { text: primaryCtaText, href: primaryCtaHref || undefined }
              : undefined
          }
          secondaryCta={
            secondaryCtaText
              ? { text: secondaryCtaText, href: secondaryCtaHref || undefined }
              : undefined
          }
        />
      </Container>
    </section>
  );
}
