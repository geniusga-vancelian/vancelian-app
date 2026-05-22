"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  SupportAsidePanel,
  hasSupportAsideContent,
  type SupportAsideContent,
} from "@/components/design-system/SupportAsidePanel";
import {
  VSectionHeader,
} from "@/components/design-system/vancelian/VSectionHeader";

export type FAQSupportAside = SupportAsideContent;

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQProps {
  items: FAQItem[];
  /**
   * Titre principal de la section. Optionnel — si vide, aucun titre n'est
   * rendu (doctrine « pas de fallback hardcodé »).
   */
  headline?: ReactNode;
  /** Surtitre / pastille au-dessus du titre. Optionnel. */
  eyebrow?: string;
  /** Description optionnelle affichée sous le titre. */
  description?: string;
  /** Module support sticky (colonne droite 30 %). */
  support?: FAQSupportAside;
  /** Libellé du bouton « tout développer ». Vide = pas de contrôle. */
  expandAllLabel?: string;
  /** Libellé du bouton « tout replier ». Vide = pas de contrôle. */
  collapseAllLabel?: string;
}

/**
 * FAQ — Vancelian Design System (`components/faq/`).
 *
 * Layout 70 / 30 : accordéon à gauche, aside support sticky à droite.
 * Un seul item ouvert à la fois ; chevron rotatif ; séparateurs 1px.
 */
function FAQItemComponent({
  item,
  isOpen,
  onToggle,
}: {
  item: FAQItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-b border-v-fg-10 last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className={cn(
          "group flex w-full min-h-[56px] cursor-pointer items-center justify-between gap-6",
          "py-5 text-left lg:min-h-[64px]",
          "font-ui font-semibold text-[18px] leading-[1.35] text-v-fg lg:text-[20px]",
          "transition-colors duration-v-base hover:text-v-fg-body motion-reduce:transition-none",
        )}
      >
        <span className="min-w-0 flex-1">{item.question}</span>
        <ChevronDown
          className={cn(
            "h-5 w-5 shrink-0 text-v-fg-muted transition-transform duration-v-base motion-reduce:transition-none",
            isOpen ? "rotate-180" : "rotate-0",
          )}
          aria-hidden
        />
      </button>

      <div
        className="grid w-full transition-[grid-template-rows] duration-v-base ease-v-in-out motion-reduce:transition-none"
        style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
      >
        <div className="min-h-0 overflow-hidden" aria-hidden={!isOpen}>
          <div
            className={cn(
              "pb-6 transition-[opacity,transform] duration-v-base motion-reduce:transition-none",
              isOpen ? "translate-y-0 opacity-100" : "-translate-y-1 opacity-0",
            )}
          >
            <p className="m-0 max-w-[640px] font-ui text-[16px] font-normal leading-[1.6] text-v-fg-body whitespace-pre-wrap">
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
  support,
  expandAllLabel,
  collapseAllLabel,
}: FAQProps) {
  const expandAllText = expandAllLabel?.trim();
  const collapseAllText = collapseAllLabel?.trim();
  const showGlobalControls =
    items.length > 0 && (Boolean(expandAllText) || Boolean(collapseAllText));
  const allowMultiple = showGlobalControls;

  const [openIndex, setOpenIndex] = useState<number | null>(items.length > 0 ? 0 : null);
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());

  const isOpen = (index: number) =>
    allowMultiple ? openItems.has(index) : openIndex === index;

  const toggleItem = (index: number) => {
    if (allowMultiple) {
      setOpenItems((prev) => {
        const next = new Set(prev);
        if (next.has(index)) next.delete(index);
        else next.add(index);
        return next;
      });
      return;
    }
    setOpenIndex((prev) => (prev === index ? null : index));
  };

  const supportAside = support ?? {};
  const showSupport = Boolean(
    supportAside.title?.trim() ||
      supportAside.description?.trim() ||
      (supportAside.ctaLabel?.trim() && supportAside.ctaHref?.trim()) ||
      (supportAside.secondaryLinkLabel?.trim() && supportAside.secondaryLinkHref?.trim()),
  );

  return (
    <section className="relative flex w-full flex-col">
      <div
        className={cn(
          "grid grid-cols-1 items-start gap-12",
          showSupport ? "lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16" : "",
        )}
      >
        <div className="flex min-w-0 flex-col gap-10">
          <VSectionHeader
            eyebrow={eyebrow}
            title={headline}
            description={description}
            titleAs="h2"
            titleSize="page"
            align="left"
            className="items-start text-left [&_*]:text-left"
          />

          {showGlobalControls ? (
            <div className="flex flex-wrap items-center gap-6">
              {expandAllText ? (
                <button
                  type="button"
                  onClick={() => {
                    if (allowMultiple) {
                      setOpenItems(new Set(items.map((_, i) => i)));
                    } else {
                      setOpenIndex(0);
                    }
                  }}
                  className="border-0 bg-transparent p-0 font-ui font-medium text-[13px] uppercase tracking-[0.05em] text-v-fg-muted underline decoration-v-fg-20 underline-offset-4 transition-colors duration-v-fast hover:text-v-fg hover:decoration-v-fg"
                >
                  {expandAllText}
                </button>
              ) : null}
              {collapseAllText ? (
                <button
                  type="button"
                  onClick={() => {
                    if (allowMultiple) {
                      setOpenItems(new Set());
                    } else {
                      setOpenIndex(null);
                    }
                  }}
                  className="border-0 bg-transparent p-0 font-ui font-medium text-[13px] uppercase tracking-[0.05em] text-v-fg-muted underline decoration-v-fg-20 underline-offset-4 transition-colors duration-v-fast hover:text-v-fg hover:decoration-v-fg"
                >
                  {collapseAllText}
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="flex w-full flex-col">
            {items.map((item, index) => (
              <FAQItemComponent
                key={index}
                item={item}
                isOpen={isOpen(index)}
                onToggle={() => toggleItem(index)}
              />
            ))}
          </div>
        </div>

        {showSupport ? <SupportAsidePanel support={supportAside} /> : null}
      </div>
    </section>
  );
}
