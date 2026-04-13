import type { ReactNode } from 'react';
import { BodyLarge } from '../design-system/Typography';

/** Titres de bloc alignés sur `ThreeKeyElementsSlide`. */
export const KEY_ELEMENT_TITLE_CLASSNAME =
  "font-['Geist:Bold',sans-serif] text-[28px] font-bold leading-[1.2] text-[#1e1c1b]";

export function KeyElementBlockTitle({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <h3 className={`${KEY_ELEMENT_TITLE_CLASSNAME} ${className}`.trim()}>{children}</h3>;
}

/** Corps aligné sur `ThreeKeyElementsSlide` (`BodyLarge` 15px / 1.35 / `#8a8a8a`). */
export function KeyElementBlockBody({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <BodyLarge className={`text-[15px] leading-[1.35] text-[#8a8a8a] ${className}`.trim()}>
      {children}
    </BodyLarge>
  );
}

/** Pictogramme par défaut dans le disque (étoile sur carré noir) — identique à l’historique 3 Key-elements. */
export function DefaultKeyPictogram() {
  return (
    <div className="flex h-[72px] w-[72px] items-center justify-center bg-[#1e1c1b]">
      <svg
        className="h-[30px] w-[30px] text-white"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden
      >
        <path d="M12 2l2.09 6.26L22 9l-7.91.74L12 16l-2.09-6.26L2 9l7.91-.74L12 2z" />
      </svg>
    </div>
  );
}

const DISC_DIM: Record<'md' | 'lg', string> = {
  lg: 'h-[160px] w-[160px]',
  /** Assez grand pour contenir le picto 72×72 sans clipper les coins du carré. */
  md: 'h-[120px] w-[120px]',
};

/** Disque gris `#f2f2f2` (avatar / picto) — `lg` = grille 3 Key-elements, `md` = quad 2×2. */
export function KeyElementRoundDisc({
  size = 'lg',
  className = '',
  children,
}: {
  size?: 'md' | 'lg';
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#f2f2f2] ${DISC_DIM[size]} ${className}`.trim()}
    >
      {children}
    </div>
  );
}

/** Cercle blanc + bord indigo + check — listes type « Lorem / Vancelian APP ». */
export function SlideChecklistGlyph({ className = '' }: { className?: string }) {
  return (
    <div
      className={`flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-full border-2 border-[#4F46E5] bg-white ${className}`.trim()}
      aria-hidden
    >
      <svg
        className="h-[20px] w-[20px] text-[#4F46E5]"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.25}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M20 6L9 17l-5-5" />
      </svg>
    </div>
  );
}
