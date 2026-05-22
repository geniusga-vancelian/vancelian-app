"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  getActiveLocaleFromPathname,
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from "@/lib/i18n/publicLocalizedRouting";
import {
  VSectionHeader,
} from "@/components/design-system/vancelian";
import { Button } from "@/components/ui/button";

interface HowItWorksStep {
  number: string;
  title: string;
  description: string;
  /** URL résolue depuis `imageMediaId` (CMS). */
  imageMediaUrl?: string;
  imageMediaAlt?: string | null;
  /** Bouton secondaire sous la description si les deux sont non vides. */
  stepButtonLabel?: string;
  stepButtonHref?: string;
}

interface HowItWorksProps {
  label?: string;
  title?: string;
  subtitle?: string;
  steps?: HowItWorksStep[];
  /** Masque les numéros 01, 02… sur les cartes. */
  hideStepNumbering?: boolean;
  /** Fond sombre (carte) — texte clair. */
  surface?: "light" | "dark";
  primaryCta?: { text: string; onClick?: () => void; href?: string };
  secondaryCta?: { text: string; onClick?: () => void; href?: string };
}

/**
 * « How it works » — Vancelian Design System.
 *
 * Pattern : header centré (eyebrow + titre éditorial + chapô) + grille de
 * cartes étapes inspirée de `product-card` du pack handoff. Chaque étape
 * porte un numéro Newsreader italic 24px (couleur muted), une image optionnelle,
 * un titre Inter SemiBold 22px et une description body 14px muted.
 *
 * Grille : pile mobile, 3 colonnes desktop (`md:flex-row md:items-stretch`).
 * Cartes : `rounded-v-card` + bordure 1px `--v-fg-20` + fond `--v-card`.
 */
function StepCard({
  step,
  hideStepNumbering,
  surface,
}: {
  step: HowItWorksStep;
  hideStepNumbering: boolean;
  surface: "light" | "dark";
}) {
  const imageUrl = typeof step.imageMediaUrl === "string" ? step.imageMediaUrl.trim() : "";
  const showImage = imageUrl.length > 0;
  const btnLabel = typeof step.stepButtonLabel === "string" ? step.stepButtonLabel.trim() : "";
  const btnHref = typeof step.stepButtonHref === "string" ? step.stepButtonHref.trim() : "";
  const showStepCta = btnLabel.length > 0 && btnHref.length > 0;

  const isDark = surface === "dark";
  const numberColor = isDark ? "text-white/65" : "text-v-fg-muted";
  const titleColor = isDark ? "text-white" : "text-v-fg";
  const descColor = isDark ? "text-white/75" : "text-v-fg-muted";
  const bgClass = isDark
    ? "bg-white/[0.04] border-white/[0.10]"
    : "bg-v-card border-v-fg-20";

  return (
    <article
      className={cn(
        "group flex h-full flex-1 flex-col rounded-v-card border p-8 shadow-v-subtle",
        "transition-shadow duration-v-base ease-v-out hover:shadow-v-medium",
        bgClass,
      )}
    >
      {!hideStepNumbering ? (
        <p
          className={cn(
            "m-0 font-display font-light italic text-[24px] leading-[1.1] tracking-[-0.01em]",
            numberColor,
          )}
        >
          {step.number}
        </p>
      ) : null}

      {showImage ? (
        <div className="mt-6 flex h-[120px] w-full items-center justify-start">
          {/* eslint-disable-next-line @next/next/no-img-element -- image étape CMS, sizing contain */}
          <img
            src={imageUrl}
            alt={step.imageMediaAlt?.trim() || ""}
            className="max-h-full max-w-full h-auto w-auto object-contain object-left"
            loading="lazy"
            decoding="async"
          />
        </div>
      ) : null}

      <h3
        className={cn(
          "m-0 font-ui font-semibold text-[22px] leading-[1.3] tracking-[0] whitespace-pre-wrap",
          !hideStepNumbering || showImage ? "mt-6" : "mt-0",
          titleColor,
        )}
      >
        {step.title}
      </h3>

      <p className={cn("m-0 mt-3 font-ui font-normal text-[14px] leading-[1.55]", descColor)}>
        {step.description}
      </p>

      {showStepCta ? (
        <div className="mt-auto pt-6">
          <Button asChild variant={isDark ? "darkPrimary" : "default"} size="sm">
            <a
              href={btnHref}
              {...(isPublicHrefExternalNavigation(btnHref)
                ? { target: "_blank" as const, rel: "noopener noreferrer" as const }
                : {})}
            >
              {btnLabel}
            </a>
          </Button>
        </div>
      ) : null}
    </article>
  );
}

function CallToAction({
  primaryCta,
  secondaryCta,
  surface,
}: {
  primaryCta?: HowItWorksProps["primaryCta"];
  secondaryCta?: HowItWorksProps["secondaryCta"];
  surface: "light" | "dark";
}) {
  if (!primaryCta && !secondaryCta) return null;
  const isDark = surface === "dark";
  return (
    <div className="flex flex-wrap items-center justify-center gap-3">
      {primaryCta ? (
        primaryCta.href ? (
          <Button asChild variant={isDark ? "darkPrimary" : "default"} size="default">
            <a
              href={primaryCta.href}
              {...(isPublicHrefExternalNavigation(primaryCta.href)
                ? { target: "_blank" as const, rel: "noopener noreferrer" as const }
                : {})}
            >
              {primaryCta.text}
            </a>
          </Button>
        ) : (
          <Button
            variant={isDark ? "darkPrimary" : "default"}
            size="default"
            onClick={primaryCta.onClick}
          >
            {primaryCta.text}
          </Button>
        )
      ) : null}
      {secondaryCta ? (
        secondaryCta.href ? (
          <Button asChild variant={isDark ? "darkSecondary" : "outline"} size="default">
            <a
              href={secondaryCta.href}
              {...(isPublicHrefExternalNavigation(secondaryCta.href)
                ? { target: "_blank" as const, rel: "noopener noreferrer" as const }
                : {})}
            >
              {secondaryCta.text}
            </a>
          </Button>
        ) : (
          <Button
            variant={isDark ? "darkSecondary" : "outline"}
            size="default"
            onClick={secondaryCta.onClick}
          >
            {secondaryCta.text}
          </Button>
        )
      ) : null}
    </div>
  );
}

export default function HowItWorks({
  // Pas de fallback hardcodé sur le surtitre (doctrine i18n CMS).
  label,
  title = "Start Your Investment \nJourney Today.",
  subtitle = "Fast, secure, and effortless investment opportunities for businesses and individuals.",
  steps = [
    {
      number: "01",
      title: "Access \nthe platform",
      description: "Create your investor account and complete compliance checks in minutes.",
    },
    {
      number: "02",
      title: "Select \nan investment",
      description: "Browse active and delivered projects with full data: location, structure, expected performance.",
    },
    {
      number: "03",
      title: "Invest in EUR\nor Crypto",
      description: "Invest fractionally with full visibility on asset structure, returns and risk factors.",
    },
  ],
  surface = "light",
  hideStepNumbering = false,
  primaryCta,
  secondaryCta,
}: HowItWorksProps) {
  const pathname = usePathname() ?? "";
  const loc = getActiveLocaleFromPathname(pathname);
  const resolveHref = React.useCallback(
    (h?: string) => {
      if (!h?.trim()) return h;
      const t = h.trim();
      if (shouldSkipLocalizePublicHref(t)) return t;
      return localizePublicInternalHref(t, loc);
    },
    [loc],
  );

  const resolvedSteps = React.useMemo(
    () =>
      steps.map((s) => ({
        ...s,
        stepButtonHref: s.stepButtonHref ? resolveHref(s.stepButtonHref) : undefined,
      })),
    [steps, resolveHref],
  );

  const primaryResolved = primaryCta
    ? { ...primaryCta, href: primaryCta.href ? resolveHref(primaryCta.href) : undefined }
    : undefined;
  const secondaryResolved = secondaryCta
    ? { ...secondaryCta, href: secondaryCta.href ? resolveHref(secondaryCta.href) : undefined }
    : undefined;

  return (
    <div
      className="relative flex w-full flex-col items-center justify-center gap-12 py-20 lg:py-24"
      data-name="How it works"
    >
      <VSectionHeader
        eyebrow={label}
        title={title}
        description={subtitle}
        titleAs="h2"
        titleSize="page"
        tone={surface === "dark" ? "inverse" : "default"}
      />

      <div className="grid w-full grid-cols-1 gap-6 md:grid-cols-3 md:items-stretch">
        {resolvedSteps.map((step, index) => (
          <StepCard
            key={index}
            step={step}
            hideStepNumbering={hideStepNumbering}
            surface={surface}
          />
        ))}
      </div>

      <CallToAction
        primaryCta={primaryResolved}
        secondaryCta={secondaryResolved}
        surface={surface}
      />
    </div>
  );
}
