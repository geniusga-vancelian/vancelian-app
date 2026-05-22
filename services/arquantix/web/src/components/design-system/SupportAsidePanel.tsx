"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface SupportAsideContent {
  title?: string;
  description?: string;
  ctaLabel?: string;
  ctaHref?: string;
  secondaryLinkLabel?: string;
  secondaryLinkHref?: string;
}

export function hasSupportAsideContent(support: SupportAsideContent): boolean {
  return Boolean(
    support.title?.trim() ||
      support.description?.trim() ||
      (support.ctaLabel?.trim() && support.ctaHref?.trim()) ||
      (support.secondaryLinkLabel?.trim() && support.secondaryLinkHref?.trim()),
  );
}

type SupportAsidePanelProps = {
  support: SupportAsideContent;
  /** Offset sticky desktop — FAQ site nav ≈ 96px ; portail topbar ≈ 72px. */
  stickyTopClassName?: string;
  className?: string;
};

/** Aside support sticky (colonne droite 30 %) — partagé FAQ + portail. */
export function SupportAsidePanel({
  support,
  stickyTopClassName = "lg:top-[96px]",
  className,
}: SupportAsidePanelProps) {
  const title = support.title?.trim();
  const description = support.description?.trim();
  const ctaLabel = support.ctaLabel?.trim();
  const ctaHref = support.ctaHref?.trim();
  const secondaryLinkLabel = support.secondaryLinkLabel?.trim();
  const secondaryLinkHref = support.secondaryLinkHref?.trim();

  const hasCta = Boolean(ctaLabel && ctaHref);
  const hasSecondary = Boolean(secondaryLinkLabel && secondaryLinkHref);

  if (!title && !description && !hasCta && !hasSecondary) {
    return null;
  }

  return (
    <aside className={cn("lg:sticky lg:self-start", stickyTopClassName, className)}>
      <div className="flex flex-col gap-5 rounded-v-card bg-v-card-warm px-6 py-8 lg:px-8">
        {title ? (
          <h3 className="m-0 font-ui text-[20px] font-semibold leading-[1.3] text-v-fg">
            {title}
          </h3>
        ) : null}

        {description ? (
          <p className="m-0 font-ui text-[16px] font-normal leading-[1.55] text-v-fg-body">
            {description}
          </p>
        ) : null}

        {hasCta ? (
          <Button variant="outline" size="default" className="w-full sm:w-auto" asChild>
            <Link href={ctaHref!}>{ctaLabel}</Link>
          </Button>
        ) : null}

        {hasSecondary ? (
          <Link
            href={secondaryLinkHref!}
            className="font-ui text-[14px] font-medium text-v-terracotta underline-offset-[3px] transition-colors duration-v-fast hover:underline"
          >
            {secondaryLinkLabel}
          </Link>
        ) : null}
      </div>
    </aside>
  );
}
