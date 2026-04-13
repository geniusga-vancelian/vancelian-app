import type { ReactNode } from 'react';
import { useId } from 'react';
import { SlideHeader } from '../design-system/SlideHeader';
import { Arrow } from '../design-system/Arrow';
import { Heading2 } from '../design-system/Typography';
import {
  DefaultKeyPictogram,
  KeyElementBlockBody,
  KeyElementBlockTitle,
  KeyElementRoundDisc,
} from './keyElementsSlideShared';

export interface WhyNowQuadItem {
  /** Pictogramme dans le disque gris ; défaut = même étoile que 3 Key-elements. */
  icon?: ReactNode;
  title: string;
  description: string;
}

export interface WhyNowQuadSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  items: WhyNowQuadItem[];
  conclusion: string;
}

function ConclusionBandTexture() {
  const uid = useId().replace(/:/g, '');
  const patternId = `why-now-quad-x-${uid}`;
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

function QuadCell({ icon, title, description }: WhyNowQuadItem) {
  return (
    <div className="flex items-start gap-[24px]">
      <KeyElementRoundDisc size="lg">{icon ?? <DefaultKeyPictogram />}</KeyElementRoundDisc>
      <div className="min-w-0 flex-1 pt-[2px]">
        <KeyElementBlockTitle className="mb-[12px]">{title}</KeyElementBlockTitle>
        <KeyElementBlockBody>{description}</KeyElementBlockBody>
      </div>
    </div>
  );
}

/**
 * Slide « timing » : mêmes blocs typo / disque que 3 Key-elements (titres 28px Geist Bold, corps 15px),
 * grille 2×2, disques 160px comme 3 Key-elements, bande conclusion — sans Confidential.
 */
export function WhyNowQuadSlide({ label, title, subtitle, items, conclusion }: WhyNowQuadSlideProps) {
  const gridItems = items.slice(0, 4);

  return (
    <div className="relative flex h-[1080px] w-[1920px] flex-col overflow-hidden bg-white">
      <div className="shrink-0">
        <SlideHeader
          label={label}
          title={title}
          subtitle={
            subtitle ? (
              <>
                <Arrow className="shrink-0" />
                <Heading2>{subtitle}</Heading2>
              </>
            ) : undefined
          }
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col justify-center px-[120px] py-[28px]">
        <div className="grid grid-cols-2 gap-x-[56px] gap-y-[80px]">
          {gridItems.map((item, index) => (
            <QuadCell key={`${item.title}-${index}`} {...item} />
          ))}
        </div>
      </div>

      <div className="relative flex h-[118px] w-full shrink-0 items-center justify-center overflow-hidden bg-[#efefef] px-[80px]">
        <ConclusionBandTexture />
        <p className="relative z-[1] text-center font-['Geist:Medium',sans-serif] text-[20px] font-medium leading-[1.4] text-[#1e1c1b]">
          {conclusion}
        </p>
      </div>
    </div>
  );
}
