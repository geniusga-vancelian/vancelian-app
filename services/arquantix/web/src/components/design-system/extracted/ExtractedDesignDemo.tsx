'use client'

import { cn } from '@/lib/utils'
import { CategoryPill, categoryPillDotPalette } from './atoms/category-pill'
import { Label } from './atoms/label'
import { PillActionButton } from './atoms/pill-action-button'
import { FigmaEyebrowLabel } from './atoms/eyebrow-label'
import { FigmaBodyText } from './atoms/body-text'
import { ParagraphLargeBold } from './atoms/paragraph-large-bold'
import { ParagraphLarge } from './atoms/paragraph-large'
import { Paragraph } from './atoms/paragraph'
import { Links } from './atoms/links'
import { figmaDsTagClassName } from './tokens/typography'
import { SectionTitle } from './atoms/section-title'
import { MainTitle } from './atoms/main-title'
import { Titlepage } from './atoms/title-page'
import { FigmaStatCard } from './molecules/figma-stat-card'
import { FigmaTestimonialCard } from './molecules/figma-testimonial-card'
import { FigmaSectionHeading } from './molecules/figma-section-heading'
import { FigmaStatsGrid } from './organisms/figma-stats-grid'
import { FigmaSimpleHero } from './organisms/figma-simple-hero'

const DEMO_STATS = [
  { value: '35+', label: 'Projects completed internationally' },
  { value: '€60M+', label: 'Total amount invested' },
  { value: '5', label: 'Countries in which we operate' },
  { value: '30%', label: 'Average gross margin of projects *' },
  { value: 'DEC 2021', label: 'Year of launch' },
  { value: '24 months', label: 'Average duration of operations' },
]

/**
 * Démo des primitives Figma (`extracted/`), pour la page `/design` ou story interne.
 */
export function ExtractedDesignDemo() {
  return (
    <div className="flex w-full max-w-[1200px] flex-col items-center gap-16 bg-white p-8 md:p-16">
      <SectionTitle size="module" align="center" color="black">
        Atomes (export Figma)
      </SectionTitle>

      <div className="flex w-full max-w-[900px] flex-col items-center gap-2 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Titlepage</p>
        <Titlepage color="#000000">Page title — hero secondary</Titlepage>
      </div>

      <div className="flex w-full max-w-[900px] flex-col items-center gap-2 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Main title</p>
        <MainTitle>Hero homepage headline</MainTitle>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <FigmaEyebrowLabel variant="outlined" color="#000" textColor="#000">
          Label 1
        </FigmaEyebrowLabel>
        <FigmaEyebrowLabel variant="outlined" color="#f3f3f3" textColor="#62656e">
          Label 2
        </FigmaEyebrowLabel>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <PillActionButton variant="primary">Primary</PillActionButton>
        <PillActionButton variant="secondary">Secondary</PillActionButton>
        <PillActionButton variant="outlined">Outlined</PillActionButton>
      </div>

      <div className="flex w-full max-w-[900px] flex-col items-center gap-2 text-center">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Label</p>
        <p className="max-w-xl text-xs text-neutral-600">
          Figma : Avenir Black 900, 10px, lh 100 %, uppercase — <code className="rounded bg-neutral-100 px-1">figmaDsLabelClassName</code>
        </p>
        <div className="rounded-lg border border-neutral-200 bg-[#f3f3f3] px-4 py-3">
          <Label className="text-black">Category</Label>
        </div>
      </div>

      <div className="flex w-full max-w-[900px] flex-col items-center gap-4">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Category pill (tag)</p>
        <p className="max-w-xl text-center text-xs text-neutral-600">
          Padding 10px, radius 8px, fond blanc, sans bordure ; point 7px + atome **Label** (10px Black) ; gap 6px ; entre
          pills <code className="rounded bg-neutral-100 px-1">gap-2</code> (8px).
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2 rounded-lg border border-neutral-200 bg-[#f3f3f3] px-6 py-6">
          <CategoryPill label="Category" dotClassName="bg-[#c4a574]" />
          <CategoryPill label="Crypto" dotClassName={categoryPillDotPalette[0]} />
          <CategoryPill label="Market news" dotClassName={categoryPillDotPalette[1]} />
          <CategoryPill label="Segment seul" />
        </div>
      </div>

      <div className="flex w-full max-w-[600px] flex-col gap-4">
        <SectionTitle size="large" align="left" color="black">
          Large Title
        </SectionTitle>
        <SectionTitle size="module" align="left" color="black">
          Section title (module)
        </SectionTitle>
        <SectionTitle size="title" align="left" color="black">
          Title (32px — étapes How it works)
        </SectionTitle>
        <SectionTitle size="small" align="left" color="black">
          Small Title
        </SectionTitle>
        <div className="w-full border-t border-neutral-200 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
            Paragraph Large Bold
          </p>
          <ParagraphLargeBold>Nom sur carte témoignage (ex.)</ParagraphLargeBold>
        </div>
        <div className="w-full border-t border-neutral-200 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
            Paragraph Large
          </p>
          <ParagraphLarge color="#f3f3f3" className="rounded bg-black px-3 py-2">
            Platform — titres colonnes footer
          </ParagraphLarge>
        </div>
        <div className="w-full border-t border-neutral-200 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">Links</p>
          <p className="mb-3 max-w-xl text-xs text-neutral-600">
            Figma : Avenir Heavy 800, 16px, lh 100 %, tracking 0 % — composant{' '}
            <code className="rounded bg-neutral-100 px-1">Links</code>, jeton{' '}
            <code className="rounded bg-neutral-100 px-1">figmaDsLinksClassName</code>.
          </p>
          <div className="rounded bg-black px-3 py-2">
            <Links color="#ffffff">Explore Projects</Links>
          </div>
        </div>
        <div className="w-full border-t border-neutral-200 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">(TAG)</p>
          <div className="rounded bg-[#f3f3f3] px-3 py-2">
            <span className={cn(figmaDsTagClassName, 'text-[#62656e]')}>Exclusive offer</span>
          </div>
        </div>
        <div className="w-full border-t border-neutral-200 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">Paragraph</p>
          <Paragraph>
            Corps de texte 14px Book — ex. citation sur une carte témoignage. Plusieurs paragraphes : conteneur
            avec <code className="rounded bg-neutral-100 px-1 text-xs">space-y-4</code> (16px).
          </Paragraph>
        </div>
        <FigmaBodyText size="large" weight="heavy" color="black">
          Large Heavy Text (FigmaBodyText)
        </FigmaBodyText>
        <FigmaBodyText size="medium" weight="roman" color="black">
          Medium Roman — corps standard
        </FigmaBodyText>
        <FigmaBodyText size="small" weight="book" color="#62656e">
          Small Book — secondaire
        </FigmaBodyText>
      </div>

      <div className="w-full rounded-[10px] bg-black p-12 md:p-16">
        <FigmaSectionHeading
          label="story"
          title="When expertise shapes luxury real estate"
          titleSize="medium"
          titleColor="#f3f3f3"
          labelColor="#f3f3f3"
        />
      </div>

      <div className="flex w-full flex-wrap gap-0.5">
        <FigmaStatCard value="35+" label="Projects completed" showBorder={false} />
        <FigmaStatCard value="€60M+" label="Total invested" showBorder />
        <FigmaStatCard value="5" label="Countries" showBorder />
      </div>

      <FigmaTestimonialCard
        author="Marie Dubois"
        role="Investisseur"
        content="Une expérience exceptionnelle avec Arquantix. Professionnalisme et transparence du début à la fin."
        backgroundColor="#f4f4f4"
      />

      <FigmaStatsGrid stats={DEMO_STATS} columns={3} />

      <FigmaSimpleHero
        title="Hero simple (texte)"
        description="Bloc hero sans média, aligné sur le module About Figma. Les couleurs sont configurables côté CMS (sections dédiées)."
        backgroundColor="#fafafa"
        textColor="#111"
      />
    </div>
  )
}
