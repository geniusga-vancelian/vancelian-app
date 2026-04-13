import type { ReactNode } from 'react';
import { SlideHeader } from '../design-system/SlideHeader';
import { Arrow } from '../design-system/Arrow';
import { Heading2 } from '../design-system/Typography';
import {
  KeyElementBlockBody,
  KeyElementBlockTitle,
  SlideChecklistGlyph,
} from './keyElementsSlideShared';

export interface ChecklistPanelItem {
  title: string;
  /** Texte principal (même typo corps que 3 Key-elements). */
  text: string;
  /** Remplace le glyphe check indigo par défaut. */
  leading?: ReactNode;
}

export interface ChecklistPanelSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  /** Lignes dans le panneau gris arrondi (souvent 4). */
  items: ChecklistPanelItem[];
}

/**
 * Liste dans un panneau `#f2f2f2` arrondi : SlideHeader + flèche + sous-titre,
 * puces check (DS), titres de ligne = `KeyElementBlockTitle` (identique colonnes 3 Key-elements), puis corps.
 */
export function ChecklistPanelSlide({ label, title, subtitle, items }: ChecklistPanelSlideProps) {
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

      <div className="flex min-h-0 flex-1 flex-col justify-center px-[120px] py-[32px]">
        <div className="rounded-[16px] bg-[#f2f2f2] px-[40px] py-[40px]">
          <ul className="m-0 flex list-none flex-col gap-[48px] p-0">
            {items.map((item, index) => (
              <li key={index} className="flex items-start gap-[24px]">
                <div className="mt-[4px] shrink-0">
                  {item.leading ?? <SlideChecklistGlyph />}
                </div>
                <div className="min-w-0 flex-1">
                  <KeyElementBlockTitle className="mb-[16px]">{item.title}</KeyElementBlockTitle>
                  <KeyElementBlockBody>{item.text}</KeyElementBlockBody>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
