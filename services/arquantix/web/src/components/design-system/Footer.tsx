"use client";

import * as React from "react";
import type { FooterSocialPlatform } from "@/lib/sections/library";
import { ParagraphLarge, SectionTitle, figmaDsLinksClassName } from "@/components/design-system/extracted";
import { cn } from "@/lib/utils";
import { Linkedin, Link2 } from "lucide-react";
import svgPaths from "./imports/Footer/svg-qd2jlli3tt";

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
  copyrightText?: string;
  /** Logo image — si absent, le logo SVG Arquantix par défaut est affiché. */
  logoUrl?: string | null;
  logoAlt?: string | null;
  legalTexts?: string[];
  socialLinks?: Array<{ platform: FooterSocialPlatform; href: string }>;
  /** Si défini et non vide, remplace les colonnes de liens statiques (CMS global). */
  navColumns?: FooterNavColumn[];
  onNewsletterSubmit?: (email: string) => void;
  newsletterSubmittingLabel?: string;
  newsletterSuccessMessage?: string;
  newsletterAlreadySubscribedMessage?: string;
  newsletterInvalidEmailMessage?: string;
  newsletterErrorMessage?: string;
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
      : platform === "youtube"
        ? "YouTube"
        : platform === "instagram"
          ? "Instagram"
          : platform === "facebook"
            ? "Facebook"
            : platform === "linkedin"
              ? "LinkedIn"
              : "Lien";

  if (platform === "x") {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={label}
        className="relative flex shrink-0 size-[24px] items-center justify-center rounded-[12px] bg-white p-[6px] transition-opacity hover:bg-gray-100 hover:opacity-90"
      >
        <div className="relative aspect-square min-h-px min-w-px flex-[1_0_0] overflow-clip">
          <svg className="absolute inset-0 block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
            <path d={svgPaths.p2c2c7000} fill="black" />
          </svg>
        </div>
      </a>
    );
  }

  if (platform === "linkedin" || platform === "other") {
    const Icon = platform === "linkedin" ? Linkedin : Link2;
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={label}
        className="relative flex size-[24px] shrink-0 items-center justify-center rounded-[12px] bg-white transition-opacity hover:bg-gray-100 hover:opacity-90"
      >
        <Icon className="size-3 text-black" strokeWidth={2} />
      </a>
    );
  }

  const pathChild =
    platform === "youtube" ? (
      <path clipRule="evenodd" d={svgPaths.p843b400} fill="black" fillRule="evenodd" />
    ) : platform === "instagram" ? (
      <path clipRule="evenodd" d={svgPaths.p14421100} fill="black" fillRule="evenodd" />
    ) : (
      <path d={svgPaths.p8dd7c00} fill="black" />
    );

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className="relative shrink-0 size-[24px] transition-opacity hover:opacity-80"
    >
      <svg className="absolute inset-0 block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 24 24">
        <rect fill="white" height="24" rx="12" width="24" />
        {pathChild}
      </svg>
    </a>
  );
}

export default function Footer({
  newsletterVisible = true,
  newsletterTitle = "Subscribe to our newsletter",
  newsletterPlaceholder = "Enter your email",
  newsletterButtonLabel = "subscribe",
  tagline = "Institutional trust. Exceptional real estate.",
  copyrightText = "© Arquantix — All rights reserved",
  logoUrl,
  logoAlt,
  navColumns,
  legalTexts = [],
  socialLinks = [],
  onNewsletterSubmit,
  newsletterSubmittingLabel = "Submitting...",
  newsletterSuccessMessage = "Thank you! You are now subscribed.",
  newsletterAlreadySubscribedMessage = "This email is already subscribed.",
  newsletterInvalidEmailMessage = "Please enter a valid email address.",
  newsletterErrorMessage = "Unable to subscribe right now. Please try again.",
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          source: "footer",
        }),
      });

      if (!response.ok) {
        throw new Error("newsletter_subscribe_failed");
      }

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

  return (
    <footer className="relative flex w-full flex-col items-stretch justify-center gap-10 bg-transparent py-12 md:gap-12 md:py-16 lg:gap-16 lg:py-20">
      {newsletterVisible ? (
        <section className="relative w-full shrink-0 bg-transparent">
          <div className="relative flex w-full flex-col gap-6 overflow-hidden pb-8 md:flex-row md:items-center md:justify-between md:pb-12">
            <SectionTitle as="h1" align="left" color="#ffffff" size="module">
              {newsletterTitle}
            </SectionTitle>

            <form
              onSubmit={handleSubmit}
              className="relative flex w-full max-w-[451px] shrink-0 items-center md:ml-auto"
            >
              <div className="relative flex h-[36px] min-h-px min-w-px flex-[1_0_0] rounded-[40px] bg-black">
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 rounded-[40px] border border-solid border-[#62656e]"
                />
                <div className="flex size-full flex-row items-center">
                  <div className="content-stretch relative flex size-full items-center pl-[24px]">
                    <input
                      type="email"
                      name="email"
                      placeholder={newsletterPlaceholder}
                      className="min-h-px min-w-px flex-[1_0_0] border-none bg-transparent font-['Avenir:Book',sans-serif] text-[14px] leading-[1.6] text-white outline-none placeholder:text-white"
                      required
                      disabled={newsletterState === "loading"}
                    />
                    <button
                      type="submit"
                      className="relative flex h-[36px] shrink-0 content-stretch items-center justify-center rounded-[40px] bg-white px-[24px] py-[11px] transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-70"
                      disabled={newsletterState === "loading"}
                    >
                      <span className="text-center font-['Avenir:Heavy',sans-serif] text-[12px] uppercase leading-[1.1] tracking-[0.06px] text-black whitespace-nowrap">
                        {newsletterState === "loading" ? newsletterSubmittingLabel : newsletterButtonLabel}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </form>
            {newsletterFeedback ? (
              <p
                className={cn(
                  "mt-3 text-right text-[12px] leading-[1.4] md:absolute md:bottom-[-24px] md:right-0",
                  newsletterState === "success" || newsletterState === "already"
                    ? "text-[#f3f3f3]"
                    : "text-[#ffb3b3]",
                )}
                role="status"
                aria-live="polite"
              >
                {newsletterFeedback}
              </p>
            ) : null}
          </div>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 hidden border-b border-solid border-[#62656e] md:block"
          />
        </section>
      ) : null}

      {/* Links Section */}
      <div className="relative flex w-full min-w-0 flex-col gap-10 lg:flex-row lg:items-start lg:gap-10">
        {/* Brand Column */}
        <div className="relative flex min-h-px min-w-0 flex-1 flex-col items-center gap-8 text-center lg:items-start lg:text-left">
          <div className="relative mx-auto h-[44.334px] w-[203px] shrink-0 lg:mx-0">
            {logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={logoUrl}
                alt={logoAlt || "Logo"}
                className="h-[44px] w-auto max-w-[203px] object-contain object-center lg:object-left"
              />
            ) : (
              <svg className="absolute inset-0 block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 203 44.334">
                <path d={svgPaths.p3e564200} fill="white" />
              </svg>
            )}
          </div>

          <p className="w-full max-w-[420px] font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-white lg:max-w-none">
            {tagline}
          </p>

          {showSocial ? (
            <div className="content-stretch relative flex shrink-0 items-start justify-center gap-[8px] lg:justify-start">
              {socialLinks.map((s, i) => (
                <SocialIconLink key={`${s.platform}-${s.href}-${i}`} platform={s.platform} href={s.href} />
              ))}
            </div>
          ) : null}
        </div>

        <nav className="grid w-full min-w-0 shrink-0 grid-cols-1 items-start gap-8 sm:grid-cols-3 sm:gap-6 lg:max-w-[676px] lg:gap-8">
          {useDynamicNav
            ? navColumns!.map((col) => (
                <div key={col.title} className="flex w-full min-w-0 flex-col items-start justify-start">
                  <ParagraphLarge color="#f3f3f3" className="mb-4 whitespace-nowrap">
                    {col.title}
                  </ParagraphLarge>
                  <div className="flex w-full flex-col gap-2">
                    {col.links.map((link, i) => (
                      <a
                        key={`${link.href}-${i}`}
                        href={link.href}
                        className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                </div>
              ))
            : (
              <>
                <div className="flex w-full min-w-0 flex-col items-start justify-start">
                  <ParagraphLarge color="#f3f3f3" className="mb-4 whitespace-nowrap">
                    Arquantix
                  </ParagraphLarge>
                  <div className="flex w-full flex-col gap-2">
                    <a
                      href="#about"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      About
                    </a>
                    <a
                      href="#projects"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Projects
                    </a>
                  </div>
                </div>

                <div className="flex w-full min-w-0 flex-col items-start justify-start">
                  <ParagraphLarge color="#f3f3f3" className="mb-4 whitespace-nowrap">
                    Help
                  </ParagraphLarge>
                  <div className="flex w-full flex-col gap-2">
                    <a href="#faq" className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}>
                      FAQ
                    </a>
                    <a
                      href="#contact"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Contact
                    </a>
                    <a
                      href="#support"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Support
                    </a>
                  </div>
                </div>

                <div className="flex w-full min-w-0 flex-col items-start justify-start">
                  <ParagraphLarge color="#f3f3f3" className="mb-4 whitespace-nowrap">
                    Legal
                  </ParagraphLarge>
                  <div className="flex w-full flex-col gap-2">
                    <a
                      href="#legal"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Legal
                    </a>
                    <a
                      href="#privacy"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Privacy policy
                    </a>
                    <a
                      href="#terms"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Terms &amp; conditions
                    </a>
                    <a
                      href="#regulatory"
                      className={cn(figmaDsLinksClassName, "w-full text-white transition-opacity hover:opacity-70")}
                    >
                      Regulatory disclosures
                    </a>
                  </div>
                </div>
              </>
            )}
        </nav>
      </div>

      <div className="content-stretch relative flex w-full shrink-0 flex-col items-start gap-[32px]">
        <div className="content-stretch relative flex w-full shrink-0 items-start">
          <p className="font-['Avenir:Book',sans-serif] text-[14px] leading-[1.6] text-[#f3f3f3]">{copyrightText}</p>
        </div>

        {legalTexts.length > 0 ? (
          <div className="content-stretch flex w-full flex-col items-start gap-[16px] font-['Avenir:Book',sans-serif] text-[14px] leading-[0] text-[#62656e]">
            {legalTexts.map((text, index) => (
              <div key={index} className="relative flex w-full shrink-0 flex-col justify-center">
                <p className="leading-[1.6] whitespace-pre-wrap">{text}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </footer>
  );
}
