"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { SectionTitle, figmaDsButtonLabelClassName } from "@/components/design-system/extracted";
import { cn } from "@/lib/utils";
import {
  getActiveLocaleFromPathname,
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from "@/lib/i18n/publicLocalizedRouting";

interface HowItWorksStep {
  number: string;
  title: string;
  description: string;
  /** URL résolue depuis `imageMediaId` (CMS) — ne pas stocker en JSON éditable. */
  imageMediaUrl?: string;
  imageMediaAlt?: string | null;
  /** Affichés ensemble : bouton pill sous la description si les deux sont non vides. */
  stepButtonLabel?: string;
  stepButtonHref?: string;
}

interface HowItWorksProps {
  label?: string;
  title?: string;
  subtitle?: string;
  steps?: HowItWorksStep[];
  /** Si true : masque les numéros d’étape (01, 02…) sur les cartes. */
  hideStepNumbering?: boolean;
  /** Fond sombre (maquette) : CTA en contour clair pour rester lisible sur noir. */
  surface?: "light" | "dark";
  primaryCta?: {
    text: string;
    onClick?: () => void;
    href?: string;
  };
  secondaryCta?: {
    text: string;
    onClick?: () => void;
    href?: string;
  };
}

function Label({ text }: { text: string }) {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0" data-name="Label">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">
        {text}
      </p>
    </div>
  );
}

function Title({ label, title }: { label?: string; title?: string }) {
  const labelText = label?.trim();
  const showTitle = Boolean(title?.trim());
  if (!labelText && !showTitle) return null;
  return (
    <div className="content-stretch flex flex-col gap-[10px] items-center relative shrink-0 w-full" data-name="Title">
      {labelText ? <Label text={labelText} /> : null}
      {showTitle ? (
        <SectionTitle as="h1" align="center" color="#000000" size="module" className="whitespace-pre-wrap">
          {title}
        </SectionTitle>
      ) : null}
    </div>
  );
}

function Text({ label, title, subtitle }: { label?: string; title?: string; subtitle?: string }) {
  const showSubtitle = Boolean(subtitle?.trim());
  return (
    <div className="content-stretch flex flex-col gap-[24px] items-center relative shrink-0 w-full" data-name="Text">
      <Title label={label} title={title} />
      {showSubtitle ? (
        <p className="w-full text-center font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] not-italic text-black">
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}

function CtaPrimary({
  text,
  onClick,
  href,
  variant = "solid",
}: {
  text: string;
  onClick?: () => void;
  href?: string;
  variant?: "solid" | "onDark";
}) {
  const Component = href ? "a" : "button";
  const ext = Boolean(href && isPublicHrefExternalNavigation(href));
  const props = href
    ? {
        href,
        ...(ext ? { target: "_blank" as const, rel: "noopener noreferrer" } : {}),
      }
    : { onClick };
  /** Inline-flex + padding Figma : largeur au contenu, 24px horizontal / 11px vertical, pill. */
  const solid =
    "inline-flex max-w-full cursor-pointer items-center justify-center rounded-full bg-black px-[24px] py-[11px] text-center no-underline shrink-0";
  const onDark =
    "inline-flex max-w-full cursor-pointer items-center justify-center rounded-full border border-white bg-transparent px-[24px] py-[11px] text-center no-underline shrink-0";

  return (
    <Component className={variant === "onDark" ? onDark : solid} data-name="CTA Primary" {...props}>
      <span className={cn(figmaDsButtonLabelClassName, "text-white whitespace-nowrap")}>
        {text}
      </span>
    </Component>
  );
}

function CtaSecondary({ text, onClick, href }: { text: string; onClick?: () => void; href?: string }) {
  const Component = href ? 'a' : 'button';
  const ext = Boolean(href && isPublicHrefExternalNavigation(href));
  const props = href
    ? {
        href,
        ...(ext ? { target: '_blank' as const, rel: 'noopener noreferrer' } : {}),
      }
    : { onClick };

  return (
    <Component
      className="relative inline-flex max-w-full shrink-0 cursor-pointer items-center justify-center rounded-[20px] border border-black bg-transparent px-[20px] py-[10px] text-center no-underline"
      data-name="Button"
      {...props}
    >
      <span className={cn(figmaDsButtonLabelClassName, "relative z-10 text-black whitespace-nowrap")}>{text}</span>
    </Component>
  );
}

function CallToAction({
  primaryCta,
  secondaryCta,
  primaryVariant = "solid",
}: {
  primaryCta?: HowItWorksProps["primaryCta"];
  secondaryCta?: HowItWorksProps["secondaryCta"];
  primaryVariant?: "solid" | "onDark";
}) {
  if (!primaryCta && !secondaryCta) return null;

  return (
    <div className="content-stretch flex gap-[8px] items-center relative shrink-0" data-name="Call to action">
      {primaryCta && (
        <CtaPrimary
          text={primaryCta.text}
          onClick={primaryCta.onClick}
          href={primaryCta.href}
          variant={primaryVariant}
        />
      )}
      {secondaryCta && (
        <CtaSecondary
          text={secondaryCta.text}
          onClick={secondaryCta.onClick}
          href={secondaryCta.href}
        />
      )}
    </div>
  );
}

function ContentHeader({
  label,
  title,
  subtitle,
}: {
  label?: string;
  title?: string;
  subtitle?: string;
}) {
  const hasAny = Boolean(label?.trim() || title?.trim() || subtitle?.trim());
  if (!hasAny) return null;
  return (
    <div className="content-stretch flex w-full flex-col items-center gap-[32px]" data-name="Content">
      <Text label={label} title={title} subtitle={subtitle} />
    </div>
  );
}

function StepCard({
  step,
  hideStepNumbering,
}: {
  step: HowItWorksStep;
  hideStepNumbering: boolean;
}) {
  const imageUrl = typeof step.imageMediaUrl === 'string' ? step.imageMediaUrl.trim() : ''
  const showImage = imageUrl.length > 0
  const btnLabel = typeof step.stepButtonLabel === 'string' ? step.stepButtonLabel.trim() : ''
  const btnHref = typeof step.stepButtonHref === 'string' ? step.stepButtonHref.trim() : ''
  const showStepCta = btnLabel.length > 0 && btnHref.length > 0

  return (
    <div className="relative flex h-full min-h-0 min-w-px flex-[1_0_0] flex-col rounded-[10px] bg-[#f3f3f3]">
      <div className="relative flex w-full flex-1 flex-col items-start gap-[16px] px-[40px] pb-[50px] pt-[26px]">
        {!hideStepNumbering ? (
          <div className="w-full shrink-0 font-['Avenir:Light',sans-serif] text-[24px] not-italic leading-[0] tracking-[-0.24px] text-[#62656e]">
            <p className="leading-[1.1]">{step.number}</p>
          </div>
        ) : null}
        {showImage ? (
          <div className="flex h-[120px] w-full min-w-0 shrink-0 items-center justify-start">
            {/* eslint-disable-next-line @next/next/no-img-element -- URL média CMS (R2 / absolue) ; contain : hauteur max 120px, largeur adaptée, sans rognage */}
            <img
              src={imageUrl}
              alt={step.imageMediaAlt?.trim() || ''}
              className="max-h-full max-w-full h-auto w-auto object-contain object-left"
              loading="lazy"
              decoding="async"
            />
          </div>
        ) : null}
        <SectionTitle
          size="title"
          align="left"
          color="#000000"
          as="h3"
          className="w-full shrink-0 whitespace-pre-wrap"
        >
          {step.title}
        </SectionTitle>
        <div className="relative w-full shrink-0">
          <p className="font-['Avenir:Book',sans-serif] text-[14px] leading-[1.6] not-italic text-[#62656e]">
            {step.description}
          </p>
        </div>
        {showStepCta ? (
          <div className="mt-auto shrink-0 self-start pt-2">
            <CtaPrimary text={btnLabel} href={btnHref} variant="solid" />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Steps({
  steps,
  hideStepNumbering = false,
}: {
  steps: HowItWorksStep[];
  hideStepNumbering?: boolean;
}) {
  return (
    <div className="content-stretch flex w-full flex-col gap-[8px] md:flex-row md:items-stretch">
      {steps.map((step, index) => (
        <div key={index} className="flex min-w-0 flex-[1_0_0] flex-row items-stretch self-stretch">
          <StepCard step={step} hideStepNumbering={hideStepNumbering} />
        </div>
      ))}
    </div>
  );
}

export default function HowItWorks({
  // ⚠️ Pas de fallback hardcodé sur le surtitre :
  // si le module CMS `how_it_works` ne fournit pas de `label`,
  // on n'affiche AUCUN surtitre côté site (évite un texte EN
  // non traduit comme « How it works » qui n'a jamais transité
  // par le pipeline i18n CMS).
  label,
  title = "Start Your Investment \nJourney Today.",
  subtitle = "Fast, secure, and effortless investment opportunities for businesses and individuals.",
  steps = [
    {
      number: "01",
      title: "Access \nthe platform",
      description: "Create your investor account and complete compliance checks in minutes."
    },
    {
      number: "02",
      title: "Select \nan investment",
      description: "Browse active and delivered projects with full data: location, structure, expected performance."
    },
    {
      number: "03",
      title: "Invest in EUR\nor Crypto",
      description: "Invest fractionally with full visibility on asset structure, returns and risk factors."
    }
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
    ? {
        ...primaryCta,
        href: primaryCta.href ? resolveHref(primaryCta.href) : undefined,
      }
    : undefined;
  const secondaryResolved = secondaryCta
    ? {
        ...secondaryCta,
        href: secondaryCta.href ? resolveHref(secondaryCta.href) : undefined,
      }
    : undefined;

  const primaryVariant = surface === "dark" ? "onDark" : "solid";
  return (
    <div
      className="relative flex w-full flex-col items-center justify-center gap-8 px-0 py-10 md:gap-10 md:py-14"
      data-name="How it works"
    >
      <ContentHeader label={label} title={title} subtitle={subtitle} />
      <Steps steps={resolvedSteps} hideStepNumbering={hideStepNumbering} />
      <CallToAction
        primaryCta={primaryResolved}
        secondaryCta={secondaryResolved}
        primaryVariant={primaryVariant}
      />
    </div>
  );
}
