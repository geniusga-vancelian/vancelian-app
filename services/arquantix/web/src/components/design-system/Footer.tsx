"use client";

import * as React from "react";
import type { FooterSocialPlatform } from "@/lib/sections/library";
import { PublicNavLink } from "@/components/site/PublicNavLink";
import { cn } from "@/lib/utils";

export type FooterNavColumn = {
  title: string;
  links: Array<{ label: string; href: string }>;
};

interface FooterProps {
  newsletterVisible?: boolean;
  newsletterTitle?: string;
  newsletterPlaceholder?: string;
  newsletterButtonLabel?: string;
  tagline?: string;
  companyAddress?: string;
  copyrightText?: string;
  secondaryNote?: string;
  logoUrl?: string | null;
  logoAlt?: string | null;
  logoMediaInvert?: boolean;
  legalTexts?: string[];
  socialLinks?: Array<{ platform: FooterSocialPlatform; href: string }>;
  navColumns?: FooterNavColumn[];
  onNewsletterSubmit?: (email: string) => void;
  newsletterSubmittingLabel?: string;
  newsletterSuccessMessage?: string;
  newsletterAlreadySubscribedMessage?: string;
  newsletterInvalidEmailMessage?: string;
  newsletterErrorMessage?: string;
}

function FooterSocialStrokeIcon({ platform }: { platform: FooterSocialPlatform }) {
  const cls = "h-5 w-5";
  if (platform === "linkedin") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M8 10v7M8 7v.01M12 17v-4a2 2 0 014 0v4M12 13v4" />
      </svg>
    );
  }
  if (platform === "x") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
        <path d="M4 4l16 16M20 4L4 20" />
      </svg>
    );
  }
  if (platform === "instagram") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r=".5" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={cls} aria-hidden>
      <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
    </svg>
  );
}

function SocialIconLink({
  platform,
  href,
}: {
  platform: FooterSocialPlatform;
  href: string;
}) {
  const label =
    platform === "x"
      ? "X"
      : platform === "instagram"
        ? "Instagram"
        : platform === "linkedin"
          ? "LinkedIn"
          : "Lien";

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className="inline-flex items-center justify-center text-[rgba(237,236,236,0.6)] transition-colors hover:text-[#EDECEC]"
    >
      <FooterSocialStrokeIcon platform={platform} />
    </a>
  );
}

export default function Footer({
  newsletterVisible = false,
  newsletterTitle = "",
  newsletterPlaceholder = "",
  newsletterButtonLabel = "",
  tagline = "",
  companyAddress = "",
  copyrightText = "",
  secondaryNote = "",
  logoUrl,
  logoAlt,
  logoMediaInvert = false,
  navColumns,
  legalTexts = [],
  socialLinks = [],
  onNewsletterSubmit,
  newsletterSubmittingLabel = "Submitting...",
  newsletterSuccessMessage = "",
  newsletterAlreadySubscribedMessage = "",
  newsletterInvalidEmailMessage = "",
  newsletterErrorMessage = "",
}: FooterProps) {
  const useDynamicNav = Array.isArray(navColumns) && navColumns.length > 0;
  const showSocial = Array.isArray(socialLinks) && socialLinks.length > 0;
  const [newsletterState, setNewsletterState] = React.useState<
    "idle" | "loading" | "success" | "already" | "invalid" | "error"
  >("idle");
  const [newsletterFeedback, setNewsletterFeedback] = React.useState("");

  const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const email = String(formData.get("email") || "").trim().toLowerCase();

    if (!isValidEmail(email)) {
      setNewsletterState("invalid");
      setNewsletterFeedback(newsletterInvalidEmailMessage);
      return;
    }

    setNewsletterState("loading");
    setNewsletterFeedback("");

    try {
      if (onNewsletterSubmit) {
        onNewsletterSubmit(email);
        setNewsletterState("success");
        setNewsletterFeedback(newsletterSuccessMessage);
        e.currentTarget.reset();
        return;
      }

      const response = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "footer" }),
      });

      if (!response.ok) throw new Error("newsletter_subscribe_failed");

      const payload = (await response.json()) as { status?: string };
      if (payload.status === "already_subscribed") {
        setNewsletterState("already");
        setNewsletterFeedback(newsletterAlreadySubscribedMessage);
        return;
      }

      setNewsletterState("success");
      setNewsletterFeedback(newsletterSuccessMessage);
      e.currentTarget.reset();
    } catch {
      setNewsletterState("error");
      setNewsletterFeedback(newsletterErrorMessage);
    }
  };

  const addressLines = companyAddress
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean);

  return (
    <footer className="relative flex w-full flex-col bg-transparent text-[#EDECEC]">
      {newsletterVisible ? (
        <section className="relative mb-10 w-full shrink-0 border-b border-white/[0.08] pb-10">
          <div className="flex w-full flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <h2 className="m-0 font-ui text-[28px] font-semibold leading-[1.1] text-white">{newsletterTitle}</h2>
            <form onSubmit={handleSubmit} className="relative flex w-full max-w-[451px] shrink-0 items-center md:ml-auto">
              <div className="relative flex h-9 w-full rounded-v-pill bg-[#141208]">
                <div aria-hidden className="pointer-events-none absolute inset-0 rounded-v-pill border border-white/15" />
                <input
                  type="email"
                  name="email"
                  placeholder={newsletterPlaceholder}
                  className="min-w-0 flex-1 border-none bg-transparent pl-6 font-ui text-[14px] text-[#EDECEC] outline-none placeholder:text-white/50"
                  required
                  disabled={newsletterState === "loading"}
                />
                <button
                  type="submit"
                  disabled={newsletterState === "loading"}
                  className="shrink-0 rounded-v-pill bg-[#EDECEC] px-6 py-[11px] font-ui text-[12px] font-semibold uppercase text-[#1A1815] transition-colors hover:bg-white disabled:opacity-70"
                >
                  {newsletterState === "loading" ? newsletterSubmittingLabel : newsletterButtonLabel}
                </button>
              </div>
            </form>
          </div>
          {newsletterFeedback ? (
            <p className="mt-3 text-right text-[12px] text-[#EDECEC]" role="status" aria-live="polite">
              {newsletterFeedback}
            </p>
          ) : null}
        </section>
      ) : null}

      <div className="grid w-full grid-cols-1 gap-10 lg:grid-cols-[2fr_repeat(4,minmax(0,1fr))] lg:gap-12">
        <div className="flex flex-col items-start text-left">
          {logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element -- média CMS
            <img
              src={logoUrl}
              alt={logoAlt || "Vancelian"}
              className="block h-[22px] w-auto"
              style={logoMediaInvert ? { filter: "brightness(0) invert(1)" } : undefined}
            />
          ) : null}

          {tagline ? (
            <p className="m-0 mt-5 font-display text-[14px] font-light italic leading-[1.5] text-[#EDECEC]">
              {tagline}
            </p>
          ) : null}

          {addressLines.length > 0 ? (
            <p className="m-0 mt-6 font-ui text-[12px] font-normal leading-[1.5] text-[rgba(237,236,236,0.5)] whitespace-pre-line">
              {addressLines.join("\n")}
            </p>
          ) : null}

          {showSocial ? (
            <ul className="mt-6 flex list-none gap-4 p-0" aria-label="Réseaux sociaux">
              {socialLinks.map((s, i) => (
                <li key={`${s.platform}-${s.href}-${i}`}>
                  <SocialIconLink platform={s.platform} href={s.href} />
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {useDynamicNav
          ? navColumns!.map((col) => (
              <nav key={col.title} className="flex min-w-0 flex-col items-start">
                <p className="m-0 mb-5 font-ui text-[11px] font-medium uppercase tracking-[0.05em] text-[#8E867A]">
                  {col.title}
                </p>
                <ul className="m-0 flex list-none flex-col gap-3 p-0">
                  {col.links.map((link, i) => (
                    <li key={`${link.href}-${i}`}>
                      <PublicNavLink
                        href={link.href}
                        className="font-ui text-[13px] font-medium leading-none text-[#EDECEC] no-underline transition-colors hover:underline hover:underline-offset-[3px]"
                      >
                        {link.label}
                      </PublicNavLink>
                    </li>
                  ))}
                </ul>
              </nav>
            ))
          : null}
      </div>

      <hr className="my-10 mb-6 border-0 border-t border-white/[0.08]" />

      <div className="flex flex-wrap items-start justify-between gap-6 font-ui text-[11px] font-normal leading-[1.5] text-[rgba(237,236,236,0.4)]">
        {copyrightText ? <p className="m-0">{copyrightText}</p> : null}
        {secondaryNote ? <p className="m-0">{secondaryNote}</p> : null}
      </div>

      {legalTexts.length > 0 ? (
        <div className="mt-6 font-ui text-[10px] font-normal leading-[1.5] text-[rgba(237,236,236,0.3)]">
          {legalTexts.map((text, index) => (
            <p key={index} className="m-0 whitespace-pre-wrap">
              {text}
            </p>
          ))}
        </div>
      ) : null}
    </footer>
  );
}
