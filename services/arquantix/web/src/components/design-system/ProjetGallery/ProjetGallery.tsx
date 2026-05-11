"use client";

import * as React from "react";
import svgPaths from "../imports/ExclusiveOffers/svg-2h39bppqnz";
import {
  FigmaEyebrowLabel,
  Paragraph,
  SectionTitle,
  figmaDsTagClassName,
} from "@/components/design-system/extracted";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { isPublicHrefExternalNavigation } from "@/lib/i18n/publicLocalizedRouting";

// Types
export interface Project {
  id: string;
  image: string;
  /** Pastille sur l’image : Coming soon / Funding / Funded (phase pool). */
  imageStatusLabel: string;
  /** Libellés (TAG) au-dessus du titre, max 2 — issus de la base (`cardTags`), sans placeholder. */
  infoTags: string[];
  /** Montant total à lever (seul), vide si non affiché. */
  amount: string;
  title: string;
  description: string;
  fundedPercentage: number;
  fundedText?: string;
  ctaLink?: string;
  /**
   * `false` = aucune lending pool rattachée : pas de bandeau bas (progression + flèche).
   * `undefined` ou `true` = comportement historique (pied affiché).
   */
  hasLendingPool?: boolean;
}

export interface TabItem {
  id: string;
  label: string;
  isActive?: boolean;
}

export interface ProjetGalleryProps {
  sectionLabel?: string;
  title: string;
  subtitle?: string;
  tabs?: TabItem[];
  projects: Project[];
  viewAllButtonText?: string;
  viewAllButtonLink?: string;
  /** Si false, le lien « Voir toutes les offres » n’est pas affiché (ex. mode « toutes les offres » CMS). */
  showViewAllButton?: boolean;
  onTabChange?: (tabId: string) => void;
  onProjectClick?: (projectId: string) => void;
}

// Composants atomiques
function SectionLabel({ text }: { text: string }) {
  return (
    <div className="content-stretch flex items-center justify-center px-[4px] py-[2px] relative rounded-[2px] shrink-0">
      <div aria-hidden="true" className="absolute border-[#62656e] border-l border-r border-solid inset-0 pointer-events-none rounded-[2px]" />
      <p className={cn(figmaDsTagClassName, 'relative shrink-0 whitespace-nowrap text-[#62656e]')}>{text}</p>
    </div>
  );
}

function InfoLabel({
  text,
  variant = "default",
  truncate = false,
  className,
}: {
  text: string;
  variant?: "default" | "primary";
  /** Libellés longs (tags CMS) : ellipsis pour ne pas empiéter sur le montant à droite. */
  truncate?: boolean;
  className?: string;
}) {
  const borderColor = variant === "primary" ? "border-black" : "border-[#62656e]";
  const textColor = variant === "primary" ? "text-black" : "text-[#62656e]";

  return (
    <div
      className={cn(
        'relative inline-flex max-w-full items-center justify-center rounded-[2px] px-[4px] py-[2px]',
        /* Sans grow : largeur = contenu ; min-w-0 + shrink permet ellipsis si la ligne manque d’espace */
        truncate ? 'min-w-0 shrink' : 'w-fit shrink-0',
        className,
      )}
    >
      <div aria-hidden="true" className={`pointer-events-none absolute inset-0 rounded-[2px] border-l border-r border-solid ${borderColor}`} />
      <p
        className={cn(
          figmaDsTagClassName,
          'relative',
          textColor,
          truncate ? 'min-w-0 max-w-full truncate' : 'shrink-0 whitespace-nowrap',
        )}
        title={truncate ? text : undefined}
      >
        {text}
      </p>
    </div>
  );
}

function ProgressBar({ percentage }: { percentage: number }) {
  const clampedPercentage = Math.min(Math.max(percentage, 0), 100);
  const widthPercentage = `${clampedPercentage}%`;

  return (
    <div className="content-stretch flex h-[4px] items-start overflow-clip relative rounded-[20px] shrink-0 w-full">
      <div className="bg-black h-full" style={{ width: widthPercentage }} />
      <div className="bg-[rgba(59,63,99,0.2)] flex-[1_0_0] h-full min-h-px min-w-px" />
    </div>
  );
}

type PillRect = { left: number; top: number; width: number; height: number; ready: boolean };

/** Barre d’onglets avec pilule noire qui coulisse sous l’onglet actif (mesure DOM + CSS transition). */
function SlidingPillTabs({
  tabs,
  activeValue,
  onValueChange,
}: {
  tabs: TabItem[];
  activeValue: string;
  onValueChange: (v: string) => void;
}) {
  const shellRef = React.useRef<HTMLDivElement>(null);
  const [pill, setPill] = React.useState<PillRect>({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
    ready: false,
  });

  const updatePill = React.useCallback(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const btn = shell.querySelector<HTMLElement>(
      '[data-slot="tabs-trigger"][data-state="active"]',
    );
    if (!btn) return;
    const sr = shell.getBoundingClientRect();
    const br = btn.getBoundingClientRect();
    setPill({
      left: br.left - sr.left,
      top: br.top - sr.top,
      width: br.width,
      height: br.height,
      ready: true,
    });
  }, []);

  React.useLayoutEffect(() => {
    updatePill();
  }, [activeValue, updatePill, tabs]);

  React.useLayoutEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const ro = new ResizeObserver(() => updatePill());
    ro.observe(shell);
    window.addEventListener("resize", updatePill);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", updatePill);
    };
  }, [updatePill]);

  return (
    <Tabs
      value={activeValue}
      onValueChange={onValueChange}
      className="flex w-full shrink-0 flex-col items-center"
    >
      <div
        ref={shellRef}
        className="relative inline-flex w-full max-w-[640px] rounded-full border border-border bg-card p-1.5 shadow-none"
      >
        <span
          aria-hidden
          className={cn(
            "pointer-events-none absolute rounded-full bg-black will-change-[left,top,width,height]",
            "transition-[left,top,width,height,opacity] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
          )}
          style={{
            left: pill.ready ? pill.left : 0,
            top: pill.ready ? pill.top : 0,
            width: Math.max(0, pill.width),
            height: Math.max(0, pill.height),
            opacity: pill.ready ? 1 : 0,
          }}
        />
        <TabsList className="relative z-[1] flex h-auto w-full min-w-0 flex-nowrap items-center justify-between gap-1 rounded-full border-0 bg-transparent p-0 text-foreground shadow-none">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className={cn(
                "relative z-[1] inline-flex h-auto min-w-0 flex-1 items-center justify-center rounded-full border border-transparent px-2 py-2.5 font-['Avenir:Heavy',sans-serif] text-[20px] leading-[1.1] tracking-[-0.01em] shadow-none md:px-4",
                "bg-transparent transition-colors duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
                "text-muted-foreground data-[state=active]:text-white",
                "data-[state=active]:border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none",
                "dark:data-[state=active]:text-white",
                "whitespace-nowrap",
              )}
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
    </Tabs>
  );
}

/** Flèche décorative en bas de carte — le clic est géré par le bouton pleine carte. */
function CardArrowIndicator() {
  return (
    <div className="pointer-events-none relative shrink-0 size-[36px]" aria-hidden>
      <svg className="absolute inset-0 block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 36 36">
        <g>
          <rect fill="black" height="36" rx="18" width="36" />
          <path d={svgPaths.p38cf7240} fill="white" />
        </g>
      </svg>
    </div>
  );
}

// Carte projet DS — exportée pour aperçus admin (Help collections, etc.).
// `role="button"` hors mode preview pour garder un `<h3>` sémantique sans `<button>` invalide.
export function DSProjectCard({
  project,
  onClick,
  preview = false,
  /** Masque la zone basse (progression / flèche) — ex. aperçu Help sans métriques articles. */
  hideFooter = false,
  /** Masque le badge FigmaEyebrowLabel sur l’image — ex. aperçu Help collections. */
  hideImageEyebrow = false,
}: {
  project: Project;
  onClick?: () => void;
  /** Aperçu statique : pas d’interaction clavier / clic (CMS admin). */
  preview?: boolean;
  hideFooter?: boolean;
  hideImageEyebrow?: boolean;
}) {
  const hideFundingFooter =
    hideFooter || project.hasLendingPool === false;
  const activate = () => {
    onClick?.();
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      activate();
    }
  };

  return (
    <div
      {...(preview
        ? { role: 'figure' as const, 'aria-label': `Aperçu — ${project.title}` }
        : {
            role: 'button' as const,
            tabIndex: 0,
            onClick: activate,
            onKeyDown,
            'aria-label': `${project.title} — ouvrir l’offre`,
          })}
      className={cn(
        'relative flex min-h-0 min-w-0 w-full flex-col items-start overflow-hidden rounded-[10px] bg-[#f3f3f3] text-left',
        preview
          ? 'cursor-default'
          : 'cursor-pointer transition-[opacity,box-shadow] hover:opacity-[0.98] hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black',
      )}
    >
      {/* Statut offre (pool) — atome Label (FigmaEyebrowLabel) */}
      <div className="h-[220px] relative shrink-0 w-full">
        <img alt={project.title} className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" src={project.image} />
        {!hideImageEyebrow ? (
          <div className="pointer-events-none relative flex size-full items-start p-[20px]">
            <FigmaEyebrowLabel variant="filled" textColor="#ffffff" className="rounded-[8px] bg-black px-[10px] py-[8px]">
              {project.imageStatusLabel}
            </FigmaEyebrowLabel>
          </div>
        ) : null}
      </div>

      {/* Description */}
      <div className="relative shrink-0 w-full">
        <div className="flex flex-col items-center size-full">
          <div className="content-stretch flex flex-col gap-[24px] items-center p-[40px] relative w-full">
            {/* Titre avec labels */}
            <div className="content-stretch flex flex-col gap-[11px] items-start relative shrink-0 w-full">
              {/* Labels d'info : max 2 tags DB à gauche ; montant total seul à droite (pas de « courant / total ») */}
              {project.infoTags.length > 0 || project.amount ? (
                <div className="flex w-full min-w-0 shrink-0 items-center gap-2">
                  {/* Tags : conteneurs à largeur contenu (w-fit) ; la ligne peut tronquer si débordement */}
                  <div className="flex min-w-0 flex-1 flex-nowrap items-center gap-1 overflow-hidden">
                    {project.infoTags.slice(0, 2).map((t, i) => (
                      <InfoLabel key={`${t}-${i}`} text={t} truncate />
                    ))}
                  </div>
                  {project.amount ? (
                    <div className="shrink-0 pl-1">
                      <InfoLabel text={project.amount} variant="primary" />
                    </div>
                  ) : null}
                </div>
              ) : null}

              {/* Titre du projet — atome DS « Title » (32px) */}
              <SectionTitle as="h3" align="left" color="#000000" size="title" className="w-full">
                {project.title}
              </SectionTitle>
            </div>

            {/* Description — atome Paragraph ; hauteur fixe 3 lignes */}
            <Paragraph
              color="#62656e"
              className={cn('relative shrink-0 text-left', 'line-clamp-3 h-[4.8em] overflow-hidden')}
            >
              {project.description}
            </Paragraph>
          </div>
        </div>
      </div>

      {/* État du financement — uniquement si lending pool (EO) ou aperçu / forçage. */}
      {!hideFundingFooter ? (
      <div className="bg-[rgba(0,0,0,0.05)] relative shrink-0 w-full">
        <div className="flex flex-row items-center justify-center size-full">
          <div className="content-stretch flex gap-[24px] items-center justify-center px-[40px] py-[24px] relative w-full">
            {/* Progress */}
            <div className="content-stretch flex flex-[1_0_0] flex-col gap-[8px] items-start min-h-px min-w-px relative">
              <div className="content-stretch flex items-center relative shrink-0 w-full">
                <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[14px] text-black uppercase whitespace-nowrap">
                  {project.fundedText || `Funded ${project.fundedPercentage}%`}
                </p>
              </div>
              <ProgressBar percentage={project.fundedPercentage} />
            </div>

            <CardArrowIndicator />
          </div>
        </div>
      </div>
      ) : null}
    </div>
  );
}

// Composant principal
export default function ProjetGallery({
  sectionLabel,
  title,
  subtitle,
  tabs = [],
  projects,
  viewAllButtonText = "Voir toutes les offres",
  viewAllButtonLink,
  showViewAllButton = true,
  onTabChange,
  onProjectClick,
}: ProjetGalleryProps) {
  const activeTabValue =
    tabs.find((t) => t.isActive)?.id ?? tabs[0]?.id ?? "";
  const hasTabs = tabs.length > 0 && Boolean(activeTabValue);

  const headerBlock = (
    <div className="content-stretch flex w-full shrink-0 flex-col gap-[24px] items-center relative">
      <div className="content-stretch flex flex-col gap-[10px] items-center relative shrink-0 w-full">
        {sectionLabel && <SectionLabel text={sectionLabel} />}
        <SectionTitle as="h1" align="center" color="#000000" size="module">
          {title}
        </SectionTitle>
      </div>
      {subtitle && (
        <p className="font-['Avenir:Roman',sans-serif] leading-[1.6] not-italic relative shrink-0 text-[18px] text-black text-center w-full">
          {subtitle}
        </p>
      )}
    </div>
  );

  return (
    <div
      className={cn(
        "relative flex w-full flex-col items-center justify-center bg-white",
        hasTabs
          ? "gap-8 pt-16 pb-12 md:gap-10 md:pb-16 lg:pb-20"
          : "gap-12 py-12 md:gap-[60px] md:py-16 lg:py-20",
      )}
    >
      {/* Avec onglets : 64px sous le hero puis tabulation en premier ; sinon ordre classique (titre d’abord). */}
      {hasTabs ? (
        <>
          <SlidingPillTabs
            tabs={tabs}
            activeValue={activeTabValue}
            onValueChange={(v) => onTabChange?.(v)}
          />
          {headerBlock}
        </>
      ) : (
        headerBlock
      )}

      {/* Galerie de projets — alignée sur la même largeur que le header (Container parent : max-w + px uniquement) */}
      <div className="relative flex w-full shrink-0 flex-col items-stretch gap-6">
        <div className="grid w-full min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-3 xl:grid-cols-3 xl:gap-2">
          {projects.map((project) => (
            <DSProjectCard key={project.id} project={project} onClick={() => onProjectClick?.(project.id)} />
          ))}
        </div>

        {/* Bouton "Voir toutes les offres" */}
        {showViewAllButton && viewAllButtonText && (
          <div className="h-[36px] relative shrink-0 w-full">
            <div className="flex flex-row items-center size-full">
              <div className="content-stretch flex items-center justify-center relative size-full">
                {viewAllButtonLink ? (
                  <a
                    className="cursor-pointer h-full relative rounded-[20px] shrink-0"
                    href={viewAllButtonLink}
                    {...(isPublicHrefExternalNavigation(viewAllButtonLink)
                      ? { target: "_blank" as const, rel: "noopener noreferrer" }
                      : {})}
                  >
                    <div aria-hidden="true" className="absolute border border-[#62656e] border-solid inset-0 pointer-events-none rounded-[20px]" />
                    <div className="flex flex-row items-center justify-center size-full">
                      <div className="content-stretch flex h-full items-center justify-center px-[20px] py-[10px] relative">
                        <div className="flex flex-col font-['Avenir:Medium',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[10px] text-black text-center tracking-[0.4px] uppercase whitespace-nowrap">
                          <p className="leading-[1.1]">{viewAllButtonText}</p>
                        </div>
                      </div>
                    </div>
                  </a>
                ) : (
                  <button className="cursor-pointer h-full relative rounded-[20px] shrink-0">
                    <div aria-hidden="true" className="absolute border border-[#62656e] border-solid inset-0 pointer-events-none rounded-[20px]" />
                    <div className="flex flex-row items-center justify-center size-full">
                      <div className="content-stretch flex h-full items-center justify-center px-[20px] py-[10px] relative">
                        <div className="flex flex-col font-['Avenir:Medium',sans-serif] justify-center leading-[0] not-italic relative shrink-0 text-[10px] text-black text-center tracking-[0.4px] uppercase whitespace-nowrap">
                          <p className="leading-[1.1]">{viewAllButtonText}</p>
                        </div>
                      </div>
                    </div>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
