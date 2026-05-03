import { ReactNode } from 'react';

import { SectionTitle } from '@/components/design-system/extracted';
import { cn } from '@/lib/utils';

interface BlockLeftAndRightProps {
  leftContent: ReactNode;
  rightContent: ReactNode;
  className?: string;
}

/**
 * BlockLeftAndRight - Composant de design system Arquantix
 *
 * Affiche deux contenus côte à côte avec un gap de 64px.
 * Utilisé pour créer des sections avec texte et image.
 */
export function BlockLeftAndRight({
  leftContent,
  rightContent,
  className = ''
}: BlockLeftAndRightProps) {
  return (
    <div
      className={cn(
        'flex min-h-0 w-full min-w-0 max-w-[1152px] flex-col items-stretch justify-center gap-8 lg:flex-row lg:items-stretch lg:gap-10 xl:gap-16',
        className,
      )}
      data-name="Section image text"
    >
      <div className="relative flex min-h-0 w-full min-w-0 flex-1 flex-col items-stretch gap-8 lg:flex-row lg:items-stretch lg:gap-10 xl:gap-16">
        {leftContent}
        {rightContent}
      </div>
    </div>
  );
}

interface TextBlockProps {
  title: string | string[];
  description: string;
  subdescription?: string;
  children?: ReactNode;
}

/**
 * TextBlock - Bloc de texte standard pour BlockLeftAndRight
 */
export function TextBlock({ title, description, subdescription, children }: TextBlockProps) {
  const titles = Array.isArray(title) ? title : [title];

  return (
    <div className="flex-[1_0_0] h-full min-h-px min-w-px relative">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col gap-[24px] items-start justify-center not-italic p-[30px] relative size-full text-black">
          <div className="flex w-full flex-col gap-0">
            {titles.map((line, index) => (
              <SectionTitle
                key={index}
                as={index === 0 ? 'h1' : 'h2'}
                align="left"
                color="#000000"
                size="module"
              >
                {line}
              </SectionTitle>
            ))}
          </div>
          <h1 className="block font-['Avenir:Roman',sans-serif] leading-[1.6] relative shrink-0 text-[18px] w-full">
            {description}
          </h1>
          {subdescription && (
            <h1 className="block font-['Avenir:Book',sans-serif] leading-[1.6] relative shrink-0 text-[14px] w-full">
              {subdescription}
            </h1>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}

interface ImageBlockProps {
  src: string;
  alt?: string;
  overlay?: ReactNode;
  imageStyle?: 'cover' | 'contain';
}

/**
 * ImageBlock - Bloc image pour BlockLeftAndRight.
 * Même logique de taille que {@link MediaTextSection} : hauteur mini explicite + cover,
 * pour éviter l’effondrement de la colonne quand l’img est en absolute (feature_grid, etc.).
 */
export function ImageBlock({ src, alt = '', overlay, imageStyle = 'cover' }: ImageBlockProps) {
  const frame = cn(
    'relative min-h-[240px] w-full min-w-0 flex-[1_0_0] overflow-hidden rounded-2xl bg-neutral-100 lg:min-h-[min(360px,50vh)]',
  )

  if (imageStyle === 'contain') {
    return (
      <div className={cn(frame, 'flex items-center justify-center p-2')}>
        <img
          alt={alt}
          className="max-h-full max-w-full object-contain object-center"
          src={src}
          loading="lazy"
          decoding="async"
        />
        {overlay ? (
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-center overflow-hidden rounded-[inherit]">
            <div className="relative flex size-full flex-col items-start justify-center p-[30px]">
              {overlay}
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div className={frame}>
      <img
        alt={alt}
        className="absolute inset-0 size-full object-cover object-center"
        src={src}
        loading="lazy"
        decoding="async"
      />
      {overlay ? (
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-center overflow-hidden rounded-[inherit]">
          <div className="relative flex size-full flex-col items-start justify-center p-[30px]">
            {overlay}
          </div>
        </div>
      ) : null}
    </div>
  )
}

interface ChecklistItem {
  text: string;
}

interface ChecklistProps {
  items: ChecklistItem[];
}

/**
 * Checklist - Liste avec icônes de validation
 */
export function Checklist({ items }: ChecklistProps) {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0">
      {items.map((item, index) => (
        <div key={index} className="content-stretch flex gap-[4px] h-[8px] items-center justify-center relative shrink-0">
          <div className="relative shrink-0 size-[14px]">
            <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14 14">
              <g>
                <rect fill="var(--fill-0, black)" height="14" rx="7" width="14" />
                <path d="M4 6.6L6.25974 9L10 5" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" />
              </g>
            </svg>
          </div>
          <p className="font-['Avenir:Heavy',sans-serif] leading-none not-italic relative shrink-0 text-[12px] text-black tracking-[-0.12px] whitespace-nowrap">
            {item.text}
          </p>
        </div>
      ))}
    </div>
  );
}

interface TextBlockWithChecklistProps {
  title: string | string[];
  description: string;
  items: ChecklistItem[];
}

/**
 * TextBlockWithChecklist - Bloc de texte avec checklist intégrée
 */
export function TextBlockWithChecklist({ title, description, items }: TextBlockWithChecklistProps) {
  const titles = Array.isArray(title) ? title : [title];

  return (
    <div className="flex-[1_0_0] h-full min-h-px min-w-px relative">
      <div className="flex flex-col justify-center size-full">
        <div className="content-stretch flex flex-col gap-[32px] items-start justify-center p-[30px] relative size-full">
          <div className="content-stretch flex flex-col gap-[24px] items-start not-italic relative shrink-0 text-black w-full">
            <div className="flex w-full flex-col gap-0">
              {titles.map((line, index) => (
                <SectionTitle
                  key={index}
                  as={index === 0 ? 'h1' : 'h2'}
                  align="left"
                  color="#000000"
                  size="module"
                >
                  {line}
                </SectionTitle>
              ))}
            </div>
            <h1 className="block font-['Avenir:Roman',sans-serif] leading-[1.6] relative shrink-0 text-[18px] w-full">
              {description}
            </h1>
          </div>
          <Checklist items={items} />
        </div>
      </div>
    </div>
  );
}
