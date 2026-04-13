import { Divider } from '../design-system/Divider';
import { SlideFooter } from '../design-system/SlideFooter';
import { MonoLabel, SectionTitle } from '../design-system/Typography';

export interface TeamSpotlightMember {
  /** Portrait pleine hauteur ; si absent, fond dégradé + initiales */
  portraitSrc?: string;
  portraitAlt?: string;
  name: string;
  /** Titre de poste (affiché en petites capitales) */
  role: string;
  paragraphs: string[];
  /** Dernier paragraphe en gras (mandat, nomination, etc.) */
  closingBold?: string;
}

export interface TeamSpotlightSlideProps {
  /** Surtitre haut (ex. TEAM) */
  label?: string;
  title: string;
  member: TeamSpotlightMember;
  /** Largeur fixe du panneau portrait (px) */
  portraitWidth?: number;
  footerText?: string;
}

function PortraitPanel({
  member,
  widthPx,
}: {
  member: TeamSpotlightMember;
  widthPx: number;
}) {
  const initials = member.name
    .split(/\s+/)
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      className="relative h-full shrink-0 overflow-hidden bg-[#252423]"
      style={{ width: widthPx }}
    >
      {member.portraitSrc ? (
        <img
          src={member.portraitSrc}
          alt={member.portraitAlt ?? member.name}
          className="h-full w-full object-cover object-top"
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-end bg-gradient-to-b from-[#454240] to-[#1a1918] pb-[18%]">
          <span className="font-['Geist:ExtraLight',sans-serif] text-[min(14vw,160px)] font-extralight text-white/30">
            {initials}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Portrait pleine hauteur à gauche + en-tête et bio sur toute la largeur restante (slide 1920×1080).
 */
export function TeamSpotlightSlide({
  label = 'TEAM',
  title,
  member,
  portraitWidth = 520,
  footerText = 'Confidential Document',
}: TeamSpotlightSlideProps) {
  return (
    <div className="relative flex h-[1080px] w-[1920px] overflow-hidden bg-white">
      <PortraitPanel member={member} widthPx={portraitWidth} />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-[#f9f7f4]">
        <header className="shrink-0 px-[72px] pb-[14px] pt-[44px]">
          <MonoLabel>{label}</MonoLabel>
          <SectionTitle className="mt-[12px] text-[56px] leading-[1.05]">{title}</SectionTitle>
          <div className="mt-[14px]">
            <Divider variant="warm" accentWidth={88} />
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col px-[72px] pb-[80px] pt-[8px]">
          <h3 className="font-['Geist:Bold',sans-serif] text-[34px] font-bold leading-[1.12] text-[#1e1c1b]">
            {member.name}
          </h3>
          <p className="mt-[12px] font-['Geist:SemiBold',sans-serif] text-[12px] font-semibold uppercase leading-[1.4] tracking-[0.14em] text-[#1e1c1b]">
            {member.role}
          </p>
          <div className="mt-[28px] min-h-0 flex-1 space-y-[20px] overflow-y-auto">
            {member.paragraphs.map((p, i) => (
              <p
                key={i}
                className="text-left font-['Geist:Regular',sans-serif] text-[18px] font-normal leading-[1.55] text-[#2c2a28]"
              >
                {p}
              </p>
            ))}
            {member.closingBold ? (
              <p className="font-['Geist:SemiBold',sans-serif] text-[18px] font-semibold leading-[1.55] text-[#1e1c1b]">
                {member.closingBold}
              </p>
            ) : null}
          </div>
        </div>
      </div>

      <SlideFooter
        showDivider={false}
        leading={<span className="text-[18px] leading-none">✶</span>}
        text={footerText}
      />
    </div>
  );
}
