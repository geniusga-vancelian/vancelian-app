import type { ReactNode } from 'react';
import { Caption, Heading2 } from './Typography';
import {
  FlutterAppColors,
  FlutterColorGroups,
  type FlutterAppColorKey,
} from '../../design-tokens/flutterAppColors';

export const colors = {
  primary: {
    black: '#1E1C1B',
    accent: '#4F46E5',
  },
  gray: {
    50: '#F2F2F2',
    400: '#8A8A8A',
    900: '#1E1C1B',
  },
  background: {
    white: '#FFFFFF',
    light: '#F2F2F2',
    overlay5: 'rgba(0, 0, 0, 0.05)',
    overlay10: 'rgba(0, 0, 0, 0.1)',
  },
  text: {
    primary: '#1E1C1B',
    secondary: '#8A8A8A',
  },
};

interface ColorSwatchProps {
  name: string;
  value: string;
  /** Ex. bg-flutter-indigo */
  utilityHint?: string;
}

export function ColorSwatch({ name, value, utilityHint }: ColorSwatchProps) {
  return (
    <div className="flex flex-col gap-2">
      <div
        className="h-32 w-32 rounded-lg border border-[#E5E7EB]"
        style={{ backgroundColor: value }}
      />
      <div className="text-sm">
        <p className="font-semibold text-[#1C1C1E]">{name}</p>
        <p className="font-mono text-xs text-[#636366]">{value}</p>
        {utilityHint ? (
          <p className="mt-1 font-mono text-[10px] text-[#8E8E93]">{utilityHint}</p>
        ) : null}
      </div>
    </div>
  );
}

function flutterKeyToTailwindBg(key: FlutterAppColorKey): string {
  const kebab = key.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
  return `bg-flutter-${kebab}`;
}

function flutterKeyToLabel(key: FlutterAppColorKey): string {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, (c) => c.toUpperCase());
}

function FlutterSwatchRow({ title, keys }: { title: string; keys: readonly FlutterAppColorKey[] }) {
  return (
    <div className="mb-10">
      <Caption className="mb-4 block font-['Geist:SemiBold',sans-serif] text-[13px] font-semibold uppercase tracking-[0.08em] text-[#48484A]">
        {title}
      </Caption>
      <div className="flex flex-wrap gap-8">
        {keys.map((key) => (
          <ColorSwatch
            key={key}
            name={flutterKeyToLabel(key)}
            value={FlutterAppColors[key]}
            utilityHint={flutterKeyToTailwindBg(key)}
          />
        ))}
      </div>
    </div>
  );
}

/** Couleurs alignées sur `AppColors` (Flutter) — variables CSS + utilitaires Tailwind. */
export function FlutterColorPalette() {
  return (
    <div className="rounded-[12px] border border-[#E5E7EB] bg-[#FAFAFA] p-10">
      <Heading2 className="mb-2 text-[28px]">Flutter — palette app</Heading2>
      <BodyMuted className="mb-8 max-w-[720px] text-[15px] leading-relaxed">
        Même référence que{' '}
        <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[13px] text-[#48484A]">
          mobile/lib/design_system/atoms/app_colors.dart
        </code>
        . Tokens TS : <code className="font-mono text-[13px]">FlutterAppColors</code> · CSS :{' '}
        <code className="font-mono text-[13px]">var(--flutter-indigo)</code> · Tailwind :{' '}
        <code className="font-mono text-[13px]">bg-flutter-purple</code>, etc.
      </BodyMuted>
      <FlutterSwatchRow title="Designer (base)" keys={[...FlutterColorGroups.designer]} />
      <FlutterSwatchRow title="Échelle de gris" keys={[...FlutterColorGroups.grayScale]} />
      <FlutterSwatchRow title="Sémantique" keys={[...FlutterColorGroups.semantic]} />
      <FlutterSwatchRow title="UI / texte" keys={[...FlutterColorGroups.ui]} />
    </div>
  );
}

function BodyMuted({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <p className={`font-['Geist:Regular',sans-serif] text-[#636366] ${className}`}>{children}</p>
  );
}

export function ColorPalette() {
  return (
    <div className="flex flex-col gap-16">
      <div>
        <Heading2 className="mb-6 text-[28px]">Slides (Figma / présentation)</Heading2>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3 md:grid-cols-5">
          <ColorSwatch name="Primary Black" value={colors.primary.black} />
          <ColorSwatch name="Accent (indigo slide)" value={colors.primary.accent} />
          <ColorSwatch name="Gray 50" value={colors.gray[50]} />
          <ColorSwatch name="Gray 400" value={colors.gray[400]} />
          <ColorSwatch name="Gray 900" value={colors.gray[900]} />
        </div>
      </div>
      <FlutterColorPalette />
    </div>
  );
}
