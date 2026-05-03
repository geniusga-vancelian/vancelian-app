"use client";

import { useState } from "react";

import { SectionTitle, figmaDsTitleSmallClassName } from "@/components/design-system/extracted";
import { cn } from "@/lib/utils";

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQProps {
  items: FAQItem[];
  /**
   * Titre principal de la section (atome « Section title »).
   * Optionnel : si vide, aucun titre n'est rendu (pas de fallback hardcodé,
   * cf. règle « contenu piloté par le CMS uniquement »).
   */
  headline?: string;
  /**
   * Surtitre / pastille au-dessus du titre. Optionnel : si non fourni
   * (ou vide), aucun bandeau n'est rendu — pas de fallback hardcodé,
   * pour éviter qu'un texte non passé par le pipeline i18n CMS apparaisse
   * sur le site (cf. règle « surtitre piloté par le CMS uniquement »).
   */
  eyebrow?: string;
  /**
   * Description optionnelle affichée sous le titre (chapô).
   * Optionnel : aucun rendu si vide. Aligné sur la convention
   * Surtitre / Titre / Description des autres modules CMS.
   */
  description?: string;
  /** Libellé du bouton « tout développer » (CMS). Vide = pas de contrôle. */
  expandAllLabel?: string;
  /** Libellé du bouton « tout replier » (CMS). Vide = pas de contrôle. */
  collapseAllLabel?: string;
}

function PlusIcon() {
  return (
    <div className="relative shrink-0 size-[12px]">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g>
          <path d="M1 6H11" stroke="white" strokeLinecap="round" strokeWidth="2" />
          <path d="M6 11L6 1" stroke="white" strokeLinecap="round" strokeWidth="2" />
        </g>
      </svg>
    </div>
  );
}

function MinusIcon() {
  return (
    <div className="relative shrink-0 size-[12px]">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g>
          <path d="M1 6H11" stroke="white" strokeLinecap="round" strokeWidth="2" />
        </g>
      </svg>
    </div>
  );
}

function FAQLabel({ text }: { text: string }) {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[#62656e] text-[14px] uppercase whitespace-nowrap">{text}</p>
    </div>
  );
}

function FAQHeader({
  headline,
  eyebrow,
  description,
}: {
  headline?: string;
  eyebrow?: string;
  description?: string;
}) {
  const eyebrowText = eyebrow?.trim();
  const headlineText = headline?.trim();
  const descriptionText = description?.trim();
  if (!eyebrowText && !headlineText && !descriptionText) {
    return null;
  }
  return (
    <div className="content-stretch flex flex-col gap-[10px] items-center relative shrink-0 w-full">
      {eyebrowText ? <FAQLabel text={eyebrowText} /> : null}
      {headlineText ? (
        <SectionTitle align="center" color="#000000" size="module">
          {headlineText}
        </SectionTitle>
      ) : null}
      {descriptionText ? (
        <p className="max-w-[720px] text-center font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black/85 whitespace-pre-wrap">
          {descriptionText}
        </p>
      ) : null}
    </div>
  );
}

const faqEase = "cubic-bezier(0.4, 0, 0.2, 1)";
const faqDuration = "0.35s";

function FAQItemComponent({ item, isOpen, onToggle }: { item: FAQItem; isOpen: boolean; onToggle: () => void }) {
  return (
    <div
      className={cn(
        "relative w-full shrink-0 overflow-hidden rounded-[10px] transition-[background-color] duration-300 ease-out motion-reduce:transition-none",
        isOpen ? "bg-[#f3f3f3]" : "bg-transparent",
      )}
    >
      {/* Zone cliquable = toute la ligne (padding + min-height WCAG ~44px) */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full min-h-[52px] cursor-pointer items-center justify-between gap-8 px-[30px] py-5 text-left md:min-h-[56px] md:py-6"
      >
        <div
          className={cn(
            "relative min-w-0 flex-1 not-italic text-black",
            figmaDsTitleSmallClassName,
            "text-[20px] md:text-[24px]",
          )}
        >
          <span className="block">{item.question}</span>
        </div>
        <div
          className={cn(
            "relative flex size-[22px] shrink-0 items-center justify-center rounded-[20px] transition-colors duration-300 ease-out motion-reduce:transition-none",
            isOpen ? "bg-[rgba(98,101,110,0.4)]" : "bg-[#62656e]",
          )}
        >
          <span
            className={cn(
              "absolute inset-0 flex items-center justify-center transition-opacity duration-300 ease-out motion-reduce:transition-none",
              isOpen ? "opacity-0" : "opacity-100",
            )}
            aria-hidden
          >
            <PlusIcon />
          </span>
          <span
            className={cn(
              "absolute inset-0 flex items-center justify-center transition-opacity duration-300 ease-out motion-reduce:transition-none",
              isOpen ? "opacity-100" : "opacity-0",
            )}
            aria-hidden
          >
            <MinusIcon />
          </span>
        </div>
      </button>

      <div
        className="grid w-full transition-[grid-template-rows] motion-reduce:transition-none"
        style={{
          gridTemplateRows: isOpen ? "1fr" : "0fr",
          transitionDuration: faqDuration,
          transitionTimingFunction: faqEase,
        }}
      >
        <div className="min-h-0 overflow-hidden" aria-hidden={!isOpen}>
          <div
            className={cn(
              "px-[30px] pb-8 transition-[opacity,transform] motion-reduce:transition-none",
              isOpen ? "translate-y-0 opacity-100" : "-translate-y-1 opacity-0",
            )}
            style={{
              transitionDuration: faqDuration,
              transitionTimingFunction: faqEase,
            }}
          >
            <p className="border-t border-black/5 pt-6 font-['Avenir:Roman',sans-serif] text-[18px] leading-[1.6] text-black whitespace-pre-wrap">
              {item.answer}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FAQ({
  items,
  headline,
  eyebrow,
  description,
  expandAllLabel,
  collapseAllLabel,
}: FAQProps) {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());

  const toggleItem = (index: number) => {
    setOpenItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const expandAllText = expandAllLabel?.trim();
  const collapseAllText = collapseAllLabel?.trim();
  const showGlobalControls =
    items.length > 0 && (Boolean(expandAllText) || Boolean(collapseAllText));

  return (
    <section className="relative flex w-full flex-col items-center justify-center px-0 py-0">
      <div className="content-stretch flex flex-col gap-[32px] items-center relative shrink-0 w-full">
        <FAQHeader headline={headline} eyebrow={eyebrow} description={description} />
        {showGlobalControls ? (
          <div className="flex flex-wrap items-center justify-center gap-4 px-2">
            {expandAllText ? (
              <button
                type="button"
                onClick={() => setOpenItems(new Set(items.map((_, i) => i)))}
                className="border-0 bg-transparent p-0 font-['Avenir:Heavy',sans-serif] text-[14px] uppercase tracking-wide text-[#62656e] underline decoration-[#62656e]/40 underline-offset-4 transition-colors hover:text-black hover:decoration-black/40"
              >
                {expandAllText}
              </button>
            ) : null}
            {collapseAllText ? (
              <button
                type="button"
                onClick={() => setOpenItems(new Set())}
                className="border-0 bg-transparent p-0 font-['Avenir:Heavy',sans-serif] text-[14px] uppercase tracking-wide text-[#62656e] underline decoration-[#62656e]/40 underline-offset-4 transition-colors hover:text-black hover:decoration-black/40"
              >
                {collapseAllText}
              </button>
            ) : null}
          </div>
        ) : null}
        <div className="content-stretch flex flex-col gap-[4px] items-start relative shrink-0 w-full">
          {items.map((item, index) => (
            <FAQItemComponent
              key={index}
              item={item}
              isOpen={openItems.has(index)}
              onToggle={() => toggleItem(index)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
