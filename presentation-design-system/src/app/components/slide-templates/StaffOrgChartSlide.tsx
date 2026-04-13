import { SlideHeader } from '../design-system/SlideHeader';
import { SlideFooter } from '../design-system/SlideFooter';
import { Heading2 } from '../design-system/Typography';

const STEM = 'w-[2px] shrink-0 bg-[#4F46E5]/35';

export interface StaffOrgNode {
  name: string;
  role: string;
  image?: string;
  children?: StaffOrgNode[];
}

export interface StaffOrgChartSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  /** Sommet de l’org (ex. direction générale). */
  root: StaffOrgNode;
  footerText?: string;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

function StaffCard({
  name,
  role,
  image,
  variant = 'default',
}: {
  name: string;
  role: string;
  image?: string;
  variant?: 'root' | 'default' | 'compact';
}) {
  const avatar =
    variant === 'root' ? 'h-[104px] w-[104px] text-[40px]' : variant === 'compact' ? 'h-[56px] w-[56px] text-[18px]' : 'h-[80px] w-[80px] text-[28px]';
  const nameSize =
    variant === 'root' ? 'text-[22px]' : variant === 'compact' ? 'text-[14px]' : 'text-[18px]';
  const roleSize = variant === 'compact' ? 'text-[11px]' : 'text-[13px]';
  const pad = variant === 'root' ? 'px-[20px] py-[18px]' : variant === 'compact' ? 'px-[12px] py-[10px]' : 'px-[16px] py-[14px]';
  const minW = variant === 'compact' ? 'min-w-[120px] max-w-[160px]' : variant === 'root' ? 'min-w-[220px] max-w-[280px]' : 'min-w-[160px] max-w-[200px]';

  return (
    <div
      className={`flex flex-col items-center rounded-[12px] bg-[#f2f2f2] text-center ${pad} ${minW}`}
    >
      <div
        className={`mb-[10px] flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-white ${avatar} font-['Geist:Bold',sans-serif] font-bold text-[#8a8a8a]`}
      >
        {image ? (
          <img src={image} alt={name} className="h-full w-full object-cover" />
        ) : (
          initials(name)
        )}
      </div>
      <p
        className={`font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] ${nameSize}`}
      >
        {name}
      </p>
      <p
        className={`mt-[6px] font-['Geist:SemiBold',sans-serif] font-semibold uppercase leading-[1.2] tracking-[0.06em] text-[#4F46E5] ${roleSize}`}
      >
        {role}
      </p>
    </div>
  );
}

function VStem({ h }: { h: number }) {
  return <div className={STEM} style={{ height: h }} />;
}

function StaffBranch({ node }: { node: StaffOrgNode }) {
  const hasTeam = Boolean(node.children?.length);

  return (
    <div className="flex min-w-0 flex-1 flex-col items-center">
      <VStem h={18} />
      <StaffCard name={node.name} role={node.role} image={node.image} variant="default" />
      {hasTeam ? (
        <>
          <VStem h={14} />
          <div className="flex w-full flex-wrap justify-center gap-[12px]">
            {node.children!.map((m) => (
              <StaffCard
                key={`${m.name}-${m.role}`}
                name={m.name}
                role={m.role}
                image={m.image}
                variant="compact"
              />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

/**
 * Organigramme **équipe / collaborateurs** : noms, rôles, photo optionnelle (même logique visuelle que TeamSlide).
 */
export function StaffOrgChartSlide({
  label,
  title,
  subtitle,
  root,
  footerText = 'Confidential Document',
}: StaffOrgChartSlideProps) {
  const branches = root.children ?? [];

  return (
    <div className="relative h-[1080px] w-[1920px] overflow-clip bg-white">
      <SlideHeader
        label={label}
        title={title}
        subtitle={subtitle ? <Heading2>{subtitle}</Heading2> : undefined}
      />

      <div className="flex min-h-0 flex-col items-center px-[100px] pb-[40px] pt-[8px]">
        <StaffCard name={root.name} role={root.role} image={root.image} variant="root" />
        {branches.length > 0 ? (
          <>
            <VStem h={22} />
            <div className="relative flex w-full max-w-[1580px] items-stretch justify-center gap-[20px] border-t-2 border-[#4F46E5]/35 pt-[2px]">
              {branches.map((node) => (
                <StaffBranch key={`${node.name}-${node.role}`} node={node} />
              ))}
            </div>
          </>
        ) : null}
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
