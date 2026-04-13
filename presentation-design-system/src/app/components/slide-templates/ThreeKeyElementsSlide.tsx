import type { ReactNode } from 'react';
import { useId } from 'react';
import { SlideHeader } from '../design-system/SlideHeader';
import { Heading2, Caption } from '../design-system/Typography';
import {
  DefaultKeyPictogram,
  KeyElementBlockBody,
  KeyElementBlockTitle,
  KeyElementRoundDisc,
} from './keyElementsSlideShared';

/** Alias historique — préférer `KeyElement`. */
export type ThreeKeyElement = KeyElement;

export interface KeyElement {
  /** Si absent : pictogramme par défaut dans le disque (même taille que l’avatar Team). */
  icon?: ReactNode;
  title: string;
  /** Ligne courte indigo / capitales — même rôle visuel que `role` sur TeamSlide. */
  tagline?: string;
  body: string;
}

export type KeyElementsColumnLayout =
  | '1-column'
  | '2-column'
  | '3-column'
  | '4-column'
  | '5-column'
  | '6-column';

export interface ThreeKeyElementsSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  /** Un ou plusieurs piliers ; la grille passe à la ligne selon `layout`. */
  elements: KeyElement[];
  /**
   * Nombre de colonnes (équivalent `layout` sur TeamSlide).
   * Si omis : déduit du nombre d’éléments (max 6 colonnes ; au-delà, grille 4 colonnes avec retours à la ligne).
   */
  layout?: KeyElementsColumnLayout;
  conclusion: string;
  confidentialText?: string;
}

const GRID_COLS: Record<KeyElementsColumnLayout, string> = {
  '1-column': 'grid-cols-1',
  '2-column': 'grid-cols-2',
  '3-column': 'grid-cols-3',
  '4-column': 'grid-cols-4',
  '5-column': 'grid-cols-5',
  '6-column': 'grid-cols-6',
};

function autoLayout(count: number): KeyElementsColumnLayout {
  if (count <= 1) return '1-column';
  if (count === 2) return '2-column';
  if (count === 3) return '3-column';
  if (count === 4) return '4-column';
  if (count === 5) return '5-column';
  if (count === 6) return '6-column';
  return '4-column';
}

function FooterWatermark() {
  const uid = useId().replace(/:/g, '');
  const patternId = `three-key-el-x-${uid}`;
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full text-[#1e1c1b]"
      aria-hidden
    >
      <defs>
        <pattern id={patternId} width={120} height={120} patternUnits="userSpaceOnUse">
          <g opacity={0.07}>
            <path d="M60 10 L110 60 L60 110 L10 60 Z" fill="none" stroke="currentColor" strokeWidth={0.8} />
            <path d="M60 25 L95 60 L60 95 L25 60 Z" fill="none" stroke="currentColor" strokeWidth={0.6} />
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${patternId})`} />
    </svg>
  );
}

/**
 * Slide « Key elements » : en-tête et grille calqués sur TeamSlide (sans avatar / LinkedIn),
 * bande de conclusion en bas. N éléments, grille 1 à 6 colonnes.
 */
export function ThreeKeyElementsSlide({
  label,
  title,
  subtitle,
  elements,
  layout: layoutProp,
  conclusion,
  confidentialText = 'Confidential Document',
}: ThreeKeyElementsSlideProps) {
  const layout = layoutProp ?? autoLayout(elements.length);
  const gridClass = GRID_COLS[layout];

  return (
    <div className="relative flex h-[1080px] w-[1920px] flex-col overflow-hidden bg-white">
      <div className="shrink-0">
        <SlideHeader
          label={label}
          title={title}
          subtitle={subtitle ? <Heading2>{subtitle}</Heading2> : undefined}
        />
      </div>

      {/*
        Zone corps seule : centrée verticalement entre le header et la bande conclusion (hors footer).
        overflow-y-auto si le contenu dépasse (ex. beaucoup de colonnes / texte long).
      */}
      <div className="flex min-h-0 flex-1 flex-col justify-center overflow-y-auto px-[120px] py-[20px]">
        <div
          className={`grid ${gridClass} gap-x-[32px] gap-y-[24px] ${layout === '1-column' ? 'justify-items-center' : ''}`}
        >
          {elements.map((el, index) => (
            <div
              key={index}
              className={`flex flex-col items-center text-center ${layout === '1-column' ? 'w-full max-w-[640px]' : ''}`}
            >
              <KeyElementRoundDisc size="lg" className="mb-[14px]">
                {el.icon ?? <DefaultKeyPictogram />}
              </KeyElementRoundDisc>

              <KeyElementBlockTitle
                className={el.tagline ? 'mb-[8px]' : 'mb-[16px]'}
              >
                {el.title}
              </KeyElementBlockTitle>

              {el.tagline ? (
                <p className="mb-[16px] font-['Geist:SemiBold',sans-serif] text-[18px] font-semibold uppercase leading-[1.2] tracking-[1px] text-[#4F46E5]">
                  {el.tagline}
                </p>
              ) : null}

              <KeyElementBlockBody>{el.body}</KeyElementBlockBody>
            </div>
          ))}
        </div>
      </div>

      <div className="relative flex h-[118px] w-full shrink-0 items-center justify-center overflow-hidden bg-[#efefef] px-[80px]">
        <FooterWatermark />
        <p className="relative z-[1] text-center font-['Geist:Medium',sans-serif] text-[20px] font-medium leading-[1.4] text-[#1e1c1b]">
          {conclusion}
        </p>
      </div>

      <div className="pointer-events-none absolute bottom-[22px] right-[60px] z-[2]">
        <Caption>{confidentialText}</Caption>
      </div>
    </div>
  );
}
