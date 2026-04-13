import type { ComponentProps, ReactNode } from 'react';
import { Logo } from "./Logo";
import { Divider } from "./Divider";
import { MonoLabel, SectionTitle } from "./Typography";

type DividerVariant = NonNullable<ComponentProps<typeof Divider>['variant']>;

interface SlideHeaderProps {
  label: string;
  title: string;
  subtitle?: ReactNode;
  showLogo?: boolean;
  logoVariant?: 'primary' | 'secondary';
  /** Défaut : accent (indigo). Ex. `coral` pour les slides offering. */
  dividerVariant?: DividerVariant;
  accentWidth?: number;
}

/**
 * Espacements verticaux resserrés pour tenir dans 1080px (évite le crop bas sur les templates denses).
 */
export function SlideHeader({
  label,
  title,
  subtitle,
  showLogo = true,
  logoVariant = 'secondary',
  dividerVariant = 'accent',
  accentWidth = 53,
}: SlideHeaderProps) {
  return (
    <div className="flex w-full flex-col px-[60px] pb-[16px] pt-[40px]">
      <div className="flex w-full shrink-0 items-center justify-between">
        <MonoLabel className="flex-1">{label}</MonoLabel>
        {showLogo && <Logo variant={logoVariant} size="small" />}
      </div>
      <SectionTitle className="mt-[16px] leading-[1.1]">{title}</SectionTitle>
      {subtitle ? (
        <div className="mt-[6px] flex items-center gap-[12px]">{subtitle}</div>
      ) : null}
      <div className="mt-[12px]">
        <Divider variant={dividerVariant} accentWidth={accentWidth} />
      </div>
    </div>
  );
}
