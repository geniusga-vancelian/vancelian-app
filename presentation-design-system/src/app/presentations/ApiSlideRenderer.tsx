import type { ReactNode } from 'react';
import { BodyLarge } from '../components/design-system/Typography';
import { SlideHeader } from '../components/design-system/SlideHeader';
import { SlideFooter } from '../components/design-system/SlideFooter';
import { TitleSlide } from '../components/slide-templates/TitleSlide';
import { TwoColumnSlide } from '../components/slide-templates/TwoColumnSlide';
import { MetricsSlide } from '../components/slide-templates/MetricsSlide';
import { TeamSlide } from '../components/slide-templates/TeamSlide';
import type { VersionDetail } from '@/lib/presentationApi';

export type ApiVersionSlide = VersionDetail['slides'][number];

function str(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : fallback;
}

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

/**
 * Rend une slide persistée API (template_key + content_json) avec les composants du design system.
 */
export function ApiSlideRenderer({
  slide,
  footerText = 'Vancelian',
}: {
  slide: ApiVersionSlide;
  footerText?: string;
}) {
  const key = slide.template_key ?? '';
  const c = asRecord(slide.content_json);

  switch (key) {
    case 'title':
      return (
        <TitleSlide
          label={str(c.badge, 'Présentation')}
          title={str(c.title, slide.slide_title ?? 'Sans titre')}
          subtitle={str(c.subtitle, slide.subtitle ?? '') || undefined}
          footerText={footerText}
        />
      );

    case 'section-divider':
      return (
        <TitleSlide
          label={str(c.kicker, 'Section')}
          title={str(c.sectionTitle, slide.slide_title ?? '—')}
          footerText={footerText}
        />
      );

    case 'two-column': {
      const leftTitle = str(c.leftTitle, 'Contenu');
      const leftBody = str(c.leftBody, '');
      const rightCaption = str(c.rightCaption, '');
      return (
        <TwoColumnSlide
          label="Contenu"
          title={slide.slide_title ?? leftTitle}
          subtitle={
            slide.subtitle ? (
              <span className="font-['Geist:Regular',sans-serif] text-[28px] text-[#1e1c1b]">{slide.subtitle}</span>
            ) : undefined
          }
          sections={[
            {
              title: leftTitle,
              content: <BodyLarge className="text-[18px] leading-[1.45] text-[#5c5c5c]">{leftBody}</BodyLarge>,
            },
          ]}
          rightContent={
            <div className="flex h-full w-full items-center justify-center bg-[#eef2ff] px-10">
              <BodyLarge className="text-[20px] leading-[1.45] text-[#374151]">{rightCaption}</BodyLarge>
            </div>
          }
          footerText={footerText}
        />
      );
    }

    case 'metrics': {
      const raw = c.metrics;
      const metrics = Array.isArray(raw)
        ? raw.map((m, i) => {
            const o = asRecord(m);
            return {
              value: str(o.value, '—'),
              label: str(o.label, `Métrique ${i + 1}`),
              description: str(o.description, '') || undefined,
            };
          })
        : [];
      const n = metrics.length;
      const layout: '2x2' | '3x2' | '4-column' =
        n <= 2 ? '2x2' : n <= 3 ? '3x2' : '4-column';
      return (
        <MetricsSlide
          label="Données"
          title={slide.slide_title ?? 'Indicateurs'}
          metrics={metrics.length ? metrics : [{ value: '—', label: 'Aucune métrique', description: undefined }]}
          layout={layout}
          footerText={footerText}
        />
      );
    }

    case 'team': {
      const raw = c.members;
      const members = Array.isArray(raw)
        ? raw.map((m) => {
            const o = asRecord(m);
            return {
              name: str(o.name, '—'),
              role: str(o.role, ''),
              bio: str(o.bio, ''),
              image: str(o.image, '') || undefined,
            };
          })
        : [];
      return (
        <TeamSlide
          label="Équipe"
          title={slide.slide_title ?? 'Membres'}
          subtitle={slide.subtitle ?? undefined}
          teamMembers={
            members.length
              ? members
              : [{ name: '—', role: '', bio: 'Ajoutez des membres dans content_json.members' }]
          }
          layout="3-column"
          footerText={footerText}
        />
      );
    }

    case 'quote':
      return (
        <TwoColumnSlide
          label="Citation"
          title={slide.slide_title ?? 'Référence'}
          quote={{
            text: <span className="text-[20px] leading-[1.5]">{str(c.quote, '')}</span>,
            attribution: str(c.author, '') || undefined,
            role: str(c.role, '') || undefined,
          }}
          sections={[]}
          rightContent={
            <div className="h-full w-full bg-gradient-to-br from-[#4F46E5]/15 to-[#f8fafc]" aria-hidden />
          }
          footerText={footerText}
        />
      );

    case 'closing':
      return (
        <TitleSlide
          label="Fin"
          title={str(c.headline, slide.slide_title ?? 'Merci')}
          subtitle={str(c.cta, slide.subtitle ?? '') || undefined}
          footerText={footerText}
        />
      );

    default: {
      const body: ReactNode = (
        <BodyLarge className="whitespace-pre-wrap font-mono text-[15px] leading-relaxed text-[#5c5c5c]">
          {key
            ? `Template « ${key} » : prévisualisation générique.\n\n${JSON.stringify(slide.content_json, null, 2)}`
            : JSON.stringify(slide.content_json, null, 2)}
        </BodyLarge>
      );
      return (
        <div className="relative flex h-[1080px] w-[1920px] flex-col overflow-clip bg-white">
          <SlideHeader
            label="Slide"
            title={slide.slide_title ?? 'Contenu brut'}
            subtitle={slide.subtitle ?? undefined}
          />
          <div className="flex-1 overflow-auto px-[120px] py-[40px]">{body}</div>
          <SlideFooter text={footerText} />
        </div>
      );
    }
  }
}
