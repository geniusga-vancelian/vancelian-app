import { SlideHeader } from '../design-system/SlideHeader';
import { SlideFooter } from '../design-system/SlideFooter';
import { Heading2 } from '../design-system/Typography';
import { FlutterAppColors, type FlutterAppColorKey } from '../../design-tokens/flutterAppColors';

export interface OrgMemberTag {
  label: string;
  /** Couleur Flutter DS (pill) */
  colorKey: FlutterAppColorKey;
}

export interface FunctionalDeptMember {
  name: string;
  title: string;
  tags?: OrgMemberTag[];
}

export interface FunctionalDepartment {
  id: string;
  name: string;
  /** Couleur d’en-tête de colonne (palette Flutter) */
  headerColorKey: FlutterAppColorKey;
  headcount: number;
  lead: { name: string; title: string };
  members: FunctionalDeptMember[];
}

export interface GovernanceSideEntry {
  line: string;
  sub?: string;
  isNew?: boolean;
}

export interface GovernanceSideBlock {
  title: string;
  entries: GovernanceSideEntry[];
}

export interface ExecPair {
  name: string;
  role: string;
}

export interface AdvancedStaffOrgChartSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  board: GovernanceSideBlock;
  surveillance: GovernanceSideBlock;
  direction: { title: string; executives: ExecPair[] };
  operationalCommittee: { title: string; executives: ExecPair[] };
  /** Ex. COO — Operations, RH & Admin */
  centerSupport: Array<{ title: string; subtitle?: string; colorKey: FlutterAppColorKey }>;
  departmentsSectionTitle?: string;
  departments: FunctionalDepartment[];
  /** Légende colorée + effectifs en bas de slide */
  showFooterLegend?: boolean;
  footerText?: string;
}

function Pill({ label, bg }: { label: string; bg: string }) {
  return (
    <span
      className="inline-flex rounded-full px-[6px] py-[1px] font-['Geist:SemiBold',sans-serif] text-[9px] font-semibold uppercase leading-none text-white"
      style={{ backgroundColor: bg }}
    >
      {label}
    </span>
  );
}

function GovernanceSideCard({ block }: { block: GovernanceSideBlock }) {
  return (
    <div
      className="flex h-full min-h-[240px] w-[200px] shrink-0 flex-col rounded-[10px] px-[14px] py-[12px]"
      style={{ backgroundColor: FlutterAppColors.gray6 }}
    >
      <p className="mb-[10px] text-center font-['Geist:Bold',sans-serif] text-[11px] font-bold uppercase leading-tight tracking-[0.06em] text-white">
        {block.title}
      </p>
      <div className="flex flex-1 flex-col gap-[8px] overflow-hidden">
        {block.entries.map((e, i) => (
          <div key={i} className="border-b border-white/10 pb-[6px] last:border-0">
            <div className="flex flex-wrap items-center gap-[4px]">
              <p className="font-['Geist:SemiBold',sans-serif] text-[10px] font-semibold leading-[1.25] text-white">
                {e.line}
              </p>
              {e.isNew ? (
                <Pill label="New" bg={FlutterAppColors.semanticPositive} />
              ) : null}
            </div>
            {e.sub ? (
              <p className="mt-[2px] font-['Geist:Regular',sans-serif] text-[9px] leading-[1.3] text-white/65">
                {e.sub}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function DottedBridge() {
  return (
    <div
      className="pointer-events-none flex flex-1 items-center self-stretch px-1"
      aria-hidden
    >
      <div className="h-0 w-full border-t border-dashed border-[#8E8E93]/55" />
    </div>
  );
}

function DepartmentColumn({ dept }: { dept: FunctionalDepartment }) {
  const accent = FlutterAppColors[dept.headerColorKey];

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div
        className="shrink-0 rounded-t-[8px] px-[8px] py-[10px] text-white"
        style={{ backgroundColor: accent }}
      >
        <p className="text-center font-['Geist:Bold',sans-serif] text-[9px] font-bold uppercase leading-[1.2] tracking-[0.04em]">
          {dept.name}
        </p>
        <p className="mt-[6px] text-center font-['Geist:Bold',sans-serif] text-[11px] font-bold leading-tight">
          {dept.lead.name}
        </p>
        <p className="mt-[2px] text-center font-['Geist:Regular',sans-serif] text-[9px] leading-tight text-white/90">
          {dept.lead.title}
        </p>
        <div className="mt-[8px] flex justify-center">
          <span className="rounded-full bg-black/20 px-[8px] py-[2px] font-['Geist:Bold',sans-serif] text-[10px] font-bold">
            {dept.headcount}
          </span>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-[8px] rounded-b-[8px] border border-t-0 border-[#E5E7EB] bg-white px-[6px] py-[8px]">
        <div
          className={`flex min-h-0 flex-1 flex-col overflow-y-auto ${
            dept.members.length > 0 && dept.members.length <= 8 ? 'justify-evenly' : 'justify-start gap-[6px]'
          }`}
        >
          {dept.members.map((m, i) => (
            <div key={i} className="border-b border-[#F3F4F6] pb-[6px] last:border-0">
              <p className="font-['Geist:Bold',sans-serif] text-[10px] font-bold leading-tight text-[#1C1C1E]">
                {m.name}
              </p>
              <p className="mt-[2px] font-['Geist:Regular',sans-serif] text-[9px] leading-[1.35] text-[#636366]">
                {m.title}
              </p>
              {m.tags?.length ? (
                <div className="mt-[4px] flex flex-wrap gap-[3px]">
                  {m.tags.map((t, j) => (
                    <Pill key={j} label={t.label} bg={FlutterAppColors[t.colorKey]} />
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Organigramme staff dense : gouvernance (board / direction / comités) + départements fonctionnels en colonnes colorées (palette Flutter).
 */
export function AdvancedStaffOrgChartSlide({
  label,
  title,
  subtitle,
  board,
  surveillance,
  direction,
  operationalCommittee,
  centerSupport,
  departmentsSectionTitle = 'Départements fonctionnels',
  departments,
  showFooterLegend = true,
  footerText = 'Confidential Document',
}: AdvancedStaffOrgChartSlideProps) {
  return (
    <div className="relative flex h-[1080px] w-[1920px] flex-col overflow-hidden bg-white">
      <div className="shrink-0">
        <SlideHeader
          label={label}
          title={title}
          subtitle={subtitle ? <Heading2>{subtitle}</Heading2> : undefined}
        />
      </div>

      {/* Gouvernance */}
      <div className="flex shrink-0 items-stretch gap-0 px-[48px] pb-[10px] pt-[4px]">
        <GovernanceSideCard block={board} />
        <DottedBridge />
        <div className="flex min-w-0 flex-1 flex-col items-center gap-[8px] px-[8px]">
          <div
            className="w-full max-w-[520px] rounded-[10px] px-[20px] py-[12px]"
            style={{ backgroundColor: FlutterAppColors.gray6 }}
          >
            <p className="mb-[8px] text-center font-['Geist:Bold',sans-serif] text-[10px] font-bold uppercase tracking-[0.12em] text-white/70">
              {direction.title}
            </p>
            <div className="flex flex-wrap justify-center gap-x-[28px] gap-y-[6px]">
              {direction.executives.map((p, i) => (
                <div key={i} className="text-center">
                  <p className="font-['Geist:Bold',sans-serif] text-[13px] font-bold text-white">{p.name}</p>
                  <p className="mt-[2px] font-['Geist:SemiBold',sans-serif] text-[10px] font-semibold uppercase tracking-[0.06em] text-white/75">
                    {p.role}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div
            className="w-full max-w-[600px] rounded-[10px] px-[16px] py-[10px]"
            style={{ backgroundColor: FlutterAppColors.purple }}
          >
            <p className="mb-[6px] text-center font-['Geist:Bold',sans-serif] text-[10px] font-bold uppercase tracking-[0.1em] text-white/90">
              {operationalCommittee.title}
            </p>
            <div className="grid grid-cols-2 gap-x-[12px] gap-y-[6px]">
              {operationalCommittee.executives.map((p, i) => (
                <div key={i} className="text-center">
                  <p className="font-['Geist:SemiBold',sans-serif] text-[11px] font-semibold text-white">{p.name}</p>
                  <p className="font-['Geist:Regular',sans-serif] text-[9px] text-white/85">{p.role}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap justify-center gap-[10px]">
            {centerSupport.map((c, i) => (
              <div
                key={i}
                className="min-w-[140px] rounded-[8px] px-[14px] py-[8px] text-center text-white"
                style={{ backgroundColor: FlutterAppColors[c.colorKey] }}
              >
                <p className="font-['Geist:Bold',sans-serif] text-[10px] font-bold uppercase leading-tight">{c.title}</p>
                {c.subtitle ? (
                  <p className="mt-[4px] font-['Geist:SemiBold',sans-serif] text-[9px] font-semibold uppercase text-white/90">
                    {c.subtitle}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
        <DottedBridge />
        <GovernanceSideCard block={surveillance} />
      </div>

      <div className="shrink-0 border-t border-[#E5E7EB] px-[48px] py-[8px]">
        <p className="text-center font-['Geist:Bold',sans-serif] text-[11px] font-bold uppercase tracking-[0.14em] text-[#48484A]">
          {departmentsSectionTitle}
        </p>
      </div>

      <div className="flex min-h-0 flex-1 gap-[6px] overflow-hidden px-[40px] pb-[8px] pt-[4px]">
        {departments.map((d) => (
          <DepartmentColumn key={d.id} dept={d} />
        ))}
      </div>

      {showFooterLegend ? (
        <div className="shrink-0 border-t border-[#E5E7EB] bg-[#FAFAFA] px-[32px] py-[10px]">
          <div className="flex flex-wrap items-end justify-center gap-x-[20px] gap-y-[6px]">
            {departments.map((d) => (
              <div key={d.id} className="flex flex-col items-center gap-[4px]">
                <span
                  className="block h-[3px] w-[72px] rounded-full"
                  style={{ backgroundColor: FlutterAppColors[d.headerColorKey] }}
                />
                <span className="font-['Geist:Medium',sans-serif] text-[10px] font-medium text-[#48484A]">
                  {d.name}: {d.headcount}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Réserve la zone du footer absolu (caption confidentielle). */}
      <div className="h-[40px] shrink-0" aria-hidden />

      <SlideFooter text={footerText} />
    </div>
  );
}
