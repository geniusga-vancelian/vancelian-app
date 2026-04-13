import { SlideHeader } from '../design-system/SlideHeader';
import { SlideFooter } from '../design-system/SlideFooter';
import { Heading2 } from '../design-system/Typography';

const STEM = 'w-[2px] shrink-0 bg-[#4F46E5]/35';

export interface CompanyOrgNode {
  /** Nom de l’entité (holding, filiale, SPV…) */
  title: string;
  /** Ex. juridiction, forme sociale */
  subtitle?: string;
  children?: CompanyOrgNode[];
}

export interface CompanyOrgChartSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  /** Racine de l’organigramme (souvent la holding ou la société mère). */
  root: CompanyOrgNode;
  footerText?: string;
}

function CompanyCard({
  title,
  subtitle,
  variant = 'default',
}: {
  title: string;
  subtitle?: string;
  variant?: 'root' | 'default' | 'compact';
}) {
  const wrap =
    variant === 'root'
      ? 'min-w-[280px] max-w-[420px] px-[32px] py-[22px]'
      : variant === 'compact'
        ? 'min-w-[140px] max-w-[220px] px-[16px] py-[12px]'
        : 'min-w-[200px] max-w-[280px] px-[22px] py-[16px]';
  const titleSize =
    variant === 'root' ? 'text-[24px]' : variant === 'compact' ? 'text-[15px]' : 'text-[19px]';

  return (
    <div className={`rounded-[12px] bg-[#f2f2f2] text-center ${wrap}`}>
      <p
        className={`font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] ${titleSize}`}
      >
        {title}
      </p>
      {subtitle ? (
        <p className="mt-[8px] font-['Geist:SemiBold',sans-serif] text-[12px] font-semibold uppercase leading-[1.3] tracking-[0.08em] text-[#4F46E5]">
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}

function VStem({ h }: { h: number }) {
  return <div className={STEM} style={{ height: h }} />;
}

function BranchColumn({ node }: { node: CompanyOrgNode }) {
  const hasSubs = Boolean(node.children?.length);

  return (
    <div className="flex min-w-0 flex-1 flex-col items-center">
      <VStem h={18} />
      <CompanyCard title={node.title} subtitle={node.subtitle} variant="default" />
      {hasSubs ? (
        <>
          <VStem h={14} />
          <div className="flex w-full flex-wrap justify-center gap-[10px]">
            {node.children!.map((sub) => (
              <CompanyCard
                key={`${sub.title}-${sub.subtitle ?? ''}`}
                title={sub.title}
                subtitle={sub.subtitle}
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
 * Organigramme **société** : entités juridiques, filiales, périmètres (pas de personnes).
 */
export function CompanyOrgChartSlide({
  label,
  title,
  subtitle,
  root,
  footerText = 'Confidential Document',
}: CompanyOrgChartSlideProps) {
  const branches = root.children ?? [];

  return (
    <div className="relative h-[1080px] w-[1920px] overflow-clip bg-white">
      <SlideHeader
        label={label}
        title={title}
        subtitle={subtitle ? <Heading2>{subtitle}</Heading2> : undefined}
      />

      <div className="flex min-h-0 flex-col items-center px-[100px] pb-[40px] pt-[8px]">
        <CompanyCard title={root.title} subtitle={root.subtitle} variant="root" />
        {branches.length > 0 ? (
          <>
            <VStem h={22} />
            <div className="relative flex w-full max-w-[1580px] items-stretch justify-center gap-[24px] border-t-2 border-[#4F46E5]/35 pt-[2px]">
              {branches.map((node) => (
                <BranchColumn key={`${node.title}-${node.subtitle ?? ''}`} node={node} />
              ))}
            </div>
          </>
        ) : null}
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
