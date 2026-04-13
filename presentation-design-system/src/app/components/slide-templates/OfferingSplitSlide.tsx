import type { ReactNode } from 'react';
import { useId, useState } from 'react';
import { Divider } from '../design-system/Divider';
import { Logo } from '../design-system/Logo';
import {
  BodyLarge,
  BodyMedium,
  Caption,
  Heading1,
  Heading2,
  MonoLabel,
  SectionTitle,
} from '../design-system/Typography';
import {
  IPHONE_PRO_APP_FRAME_SPEC,
  IPHONE_PRO_DEVICE_VECTOR_SPEC,
  type IphoneProAppFrameSpec,
} from '../../design-tokens/iphoneProAppFrame';

const SLIDE_W = 1920;
const SLIDE_H = 1080;
/** 80 % de la hauteur slide — hauteur du device (cadre + écran). */
export const OFFERING_IPHONE_DEVICE_HEIGHT = SLIDE_H * 0.8;
/**
 * Décalage du raster **dans** la zone écran uniquement (px à l’échelle du mockup), PNG + SVG.
 * Ne change ni la taille ni la position du cadre sur la slide (`phoneLeft`, `deviceW` × `deviceH`).
 */
const OFFERING_IPHONE_SCREEN_NUDGE_Y_PX = 4;

/**
 * Hauteur réservée sous le header pleine largeur (label, titre, sous-titre, divider) pour que le corps
 * de la colonne gauche ne passe pas sous le header.
 */
const OFFERING_HEADER_RESERVED_PX = 212;

/**
 * Position `top` du trait accent sous le sous-titre (aligné typo Geist : MonoLabel 24px / SectionTitle 60px ×1.2 / Heading2 32px ×1.2).
 * Utilisé pour un calque séparé avec z-index bas afin que le mockup iPhone passe par-dessus.
 */
function offeringAccentDividerTopPx(hasSubtitle: boolean): number {
  const pt = 40;
  const monoLogoRow = 30;
  const titleMt = 16;
  const sectionTitleBlock = 72;
  const dividerMt = 12;
  if (!hasSubtitle) {
    return pt + monoLogoRow + titleMt + sectionTitleBlock + dividerMt;
  }
  return pt + monoLogoRow + titleMt + sectionTitleBlock + 6 + 39 + dividerMt;
}

/** Fond colonne droite par défaut (gris très clair, aligné usage « page »). */
export const OFFERING_RIGHT_PANEL_BG = '#F5F5F5';

/** IDs picsum.photos utilisables pour un tirage « au hasard » (1…N). */
const PICSUM_RANDOM_ID_MAX = 200;

export interface OfferingFeature {
  title: string;
  description: string;
}

/** Bloc stats / métadonnées dans la colonne droite (photo + overlay), typo DS. */
export interface OfferingRightHighlight {
  label: string;
  value: string;
  description?: string;
}

export interface OfferingSplitSlideProps {
  label: string;
  title: string;
  /** Sous-titre sous le SectionTitle (même rythme que Team / Roadmap). */
  subtitle?: string;
  intro: string;
  paragraphs: string[];
  features: OfferingFeature[];
  /** Image de fond optionnelle par-dessus le gris clair. */
  rightBackgroundSrc?: string;
  rightBackgroundAlt?: string;
  /** Colonne droite : traits accent indigo + légende + valeur (+ description optionnelle). */
  rightHighlights?: OfferingRightHighlight[];
  /** Petit texte légal / disclaimer sous les highlights (colonne droite). */
  rightFootnote?: string;
  centerScreenSrc?: string;
  centerScreenAlt?: string;
  centerScreen?: ReactNode;
  deviceFrameSrc?: string;
  frameSpec?: IphoneProAppFrameSpec;
  leftWidthPercent?: number;
  phoneStraddleOffsetPx?: number;
}

export function OfferingIphoneDevice({
  screenSrc,
  screenAlt = '',
  screen,
  frameSpec: frameSpecProp,
  /** PNG opaque legacy ; sans valeur, cadre vectoriel fin (`IPHONE_PRO_DEVICE_VECTOR_SPEC`). */
  frameSrc,
  className = '',
}: {
  screenSrc?: string;
  screenAlt?: string;
  screen?: ReactNode;
  frameSrc?: string;
  frameSpec?: IphoneProAppFrameSpec;
  className?: string;
}) {
  const uid = useId().replace(/:/g, '');
  const maskId = `iphone-m-${uid}`;
  const [picsumId] = useState(() => Math.floor(Math.random() * PICSUM_RANDOM_ID_MAX) + 1);

  const frameSpec =
    frameSpecProp ?? (frameSrc ? IPHONE_PRO_APP_FRAME_SPEC : IPHONE_PRO_DEVICE_VECTOR_SPEC);

  const deviceH = OFFERING_IPHONE_DEVICE_HEIGHT;
  const s = deviceH / frameSpec.assetHeight;
  const deviceW = frameSpec.assetWidth * s;
  const r = frameSpec.screenRect;
  const island = frameSpec.dynamicIsland;
  const outerRx = frameSpec.outerRx;
  const aw = frameSpec.assetWidth;
  const ah = frameSpec.assetHeight;

  /** Même géométrie en px que le trou du masque SVG (un seul « vrai » arrondi, pas deux SVG). */
  const screenPx = {
    left: r.x * s,
    top: r.y * s,
    width: r.w * s,
    height: r.h * s,
    radius: r.radius * s,
  };

  const slot = screenPx;

  const picsumW = Math.max(240, Math.round(r.w));
  const picsumH = Math.max(480, Math.round(r.h));
  const randomInteriorSrc = `https://picsum.photos/id/${picsumId}/${picsumW}/${picsumH}`;

  const screenImgClassName =
    'pointer-events-none absolute inset-0 m-0 block size-full max-h-none max-w-none object-cover object-center';

  const slotBodyPng = (
    <div
      className="relative h-full min-h-0 w-full min-w-0"
      style={{ transform: `translateY(${OFFERING_IPHONE_SCREEN_NUDGE_Y_PX}px)` }}
    >
      {screen != null ? (
        <div className="absolute inset-0 min-h-0 min-w-0 overflow-hidden [&_img]:pointer-events-none [&_img]:absolute [&_img]:inset-0 [&_img]:m-0 [&_img]:block [&_img]:size-full [&_img]:max-h-none [&_img]:max-w-none [&_img]:object-cover [&_img]:object-center">
          {screen}
        </div>
      ) : screenSrc ? (
        <img src={screenSrc} alt={screenAlt} className={screenImgClassName} />
      ) : (
        <img
          src={randomInteriorSrc}
          alt={screenAlt || 'Aperçu placé au hasard (picsum.photos)'}
          className={screenImgClassName}
        />
      )}
    </div>
  );

  if (frameSrc) {
    return (
      <div
        className={`relative shrink-0 bg-transparent ${className}`}
        style={{ width: deviceW, height: deviceH }}
      >
        {/*
          Asset `iphone-pro-app-frame` : image opaque (sans trou alpha) → le cadre en dessous,
          contenu écran au-dessus dans la zone slot. Avec un PNG à trou transparent, inverser les z-index.
        */}
        <img
          src={frameSrc}
          alt=""
          className="pointer-events-none absolute inset-0 z-0 h-full w-full object-contain"
          draggable={false}
        />
        <div
          className="absolute z-10 overflow-hidden bg-black"
          style={{
            left: slot.left,
            top: slot.top,
            width: slot.width,
            height: slot.height,
            borderRadius: slot.radius,
          }}
        >
          {slotBodyPng}
        </div>
      </div>
    );
  }

  const interiorLabel =
    screenAlt || (screenSrc ? screenAlt : 'Aperçu placé au hasard (picsum.photos)');

  const svgCommon = {
    viewBox: `0 0 ${aw} ${ah}`,
    preserveAspectRatio: 'xMidYMid meet' as const,
    xmlns: 'http://www.w3.org/2000/svg',
  };

  return (
    <div
      role="img"
      aria-label={interiorLabel}
      className={`relative shrink-0 bg-transparent ${className}`}
      style={{ width: deviceW, height: deviceH }}
    >
      {/*
        Écran en HTML (px) = même boîte que le trou du masque SVG : évite le décalage coins entre deux viewBox.
        Cadre = seul SVG au-dessus (z-10).
      */}
      <div
        className="pointer-events-none absolute z-0 overflow-hidden bg-black"
        style={{
          left: screenPx.left,
          top: screenPx.top,
          width: screenPx.width,
          height: screenPx.height,
          borderRadius: screenPx.radius,
        }}
      >
        {slotBodyPng}
      </div>
      <svg {...svgCommon} className="pointer-events-none absolute inset-0 z-10 block size-full" aria-hidden>
        <defs>
          <mask id={maskId}>
            <rect width={aw} height={ah} rx={outerRx} fill="white" />
            <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={r.radius} ry={r.radius} fill="black" />
            <rect x={island.x} y={island.y} width={island.w} height={island.h} rx={island.r} ry={island.r} fill="black" />
          </mask>
        </defs>
        <rect width={aw} height={ah} rx={outerRx} fill="#18181b" mask={`url(#${maskId})`} />
        <rect
          x={island.x}
          y={island.y}
          width={island.w}
          height={island.h}
          rx={island.r}
          ry={island.r}
          fill="#0a0a0a"
        />
      </svg>
    </div>
  );
}

function DashBullet() {
  return <span className="mt-[10px] h-px w-[22px] shrink-0 bg-[#C4C4C4]" aria-hidden />;
}

function OfferingRightHighlightBlock({ label, value, description }: OfferingRightHighlight) {
  return (
    <div className="flex flex-col gap-[8px]">
      <div className="h-0 w-[48px] shrink-0 overflow-hidden">
        <Divider variant="accent" accentWidth={42} className="min-w-[200px]" />
      </div>
      <Caption className="!text-[14px] !leading-snug !text-white/90">{label}</Caption>
      <Heading2 className="!font-semibold !leading-[1.2] !text-white">{value}</Heading2>
      {description ? (
        <BodyMedium className="!text-[16px] !leading-snug !text-white/80">{description}</BodyMedium>
      ) : null}
    </div>
  );
}

export function OfferingSplitSlide({
  label,
  title,
  subtitle,
  intro,
  paragraphs,
  features,
  rightBackgroundSrc,
  rightBackgroundAlt = '',
  rightHighlights,
  rightFootnote,
  centerScreenSrc,
  centerScreenAlt = '',
  centerScreen,
  deviceFrameSrc,
  frameSpec,
  /** Largeur colonne gauche ; le téléphone est centré sur la jonction gauche|droite (moitié à gauche, moitié à droite). */
  leftWidthPercent = 60,
  /** Défaut : moitié de la largeur du device → centre du mockup sur `leftWidthPercent` (ex. 60 %). */
  phoneStraddleOffsetPx,
}: OfferingSplitSlideProps) {
  const split = `${leftWidthPercent}%`;
  const layoutSpec =
    frameSpec ?? (deviceFrameSrc ? IPHONE_PRO_APP_FRAME_SPEC : IPHONE_PRO_DEVICE_VECTOR_SPEC);
  const s = OFFERING_IPHONE_DEVICE_HEIGHT / layoutSpec.assetHeight;
  const deviceW = layoutSpec.assetWidth * s;
  const offset = phoneStraddleOffsetPx ?? Math.round(deviceW / 2);
  const phoneLeft = `calc(${split} - ${offset}px)`;

  const titleBlockMaxW = (SLIDE_W * leftWidthPercent) / 100 - 60;
  const accentDividerTopPx = offeringAccentDividerTopPx(Boolean(subtitle));
  const leftBodyPaddingTop = Math.max(OFFERING_HEADER_RESERVED_PX, accentDividerTopPx + 14);

  return (
    <div className="relative h-[1080px] w-[1920px] overflow-hidden bg-white">
      <div
        className="absolute left-0 top-0 z-[1] flex h-full flex-col bg-white"
        style={{ width: split }}
      >
        <div
          className="flex min-h-0 flex-1 flex-col justify-center overflow-hidden px-[60px] pb-[56px] pr-[min(280px,15vw)]"
          style={{ paddingTop: leftBodyPaddingTop }}
        >
          <Heading1>{intro}</Heading1>

          {paragraphs.map((p, i) => (
            <BodyLarge
              key={i}
              className={`leading-[1.45] !text-[#48484A] ${i === 0 ? 'mt-[22px]' : 'mt-[16px]'}`}
            >
              {p}
            </BodyLarge>
          ))}

          <ul className="mt-[28px] flex list-none flex-col gap-[22px]">
            {features.map((f, i) => (
              <li key={i} className="flex gap-[14px]">
                <DashBullet />
                <div className="min-w-0">
                  <BodyLarge className="!font-semibold leading-[1.35] !text-[#1e1c1b]">
                    {f.title}
                  </BodyLarge>
                  <BodyMedium className="mt-[8px] leading-[1.45] !text-[#8a8a8a]">
                    {f.description}
                  </BodyMedium>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div
        className="absolute right-0 top-0 z-0 h-full overflow-hidden"
        style={{
          width: `${100 - leftWidthPercent}%`,
          backgroundColor: OFFERING_RIGHT_PANEL_BG,
        }}
      >
        {rightBackgroundSrc ? (
          <img
            src={rightBackgroundSrc}
            alt={rightBackgroundAlt}
            className="h-full w-full object-cover object-center opacity-90"
          />
        ) : null}
        {rightHighlights != null && rightHighlights.length > 0 ? (
          <>
            <div
              className="pointer-events-none absolute inset-0 bg-gradient-to-l from-black/70 via-black/40 to-transparent"
              aria-hidden
            />
            <div className="pointer-events-none absolute inset-0 z-[2] flex flex-col justify-center pr-[132px] pl-[28%] pt-[120px] pb-[88px]">
              <div className="ml-auto flex w-full max-w-[380px] flex-col gap-[32px]">
                {rightHighlights.map((item, i) => (
                  <OfferingRightHighlightBlock key={`${item.label}-${i}`} {...item} />
                ))}
              </div>
              {rightFootnote ? (
                <div className="pointer-events-none absolute bottom-[48px] right-[132px] max-w-[min(520px,42vw)] text-right">
                  <Caption className="!text-[11px] !leading-[1.45] !text-white/75">{rightFootnote}</Caption>
                </div>
              ) : null}
            </div>
          </>
        ) : null}
      </div>

      {/* Trait accent derrière le mockup (z-4 sous le téléphone z-10) ; texte du header au-dessus (z-20). */}
      <div
        className="pointer-events-none absolute left-0 right-0 z-[4] px-[60px]"
        style={{ top: accentDividerTopPx }}
      >
        <div className="min-w-0" style={{ maxWidth: Math.max(0, titleBlockMaxW) }}>
          <Divider variant="accent" accentWidth={64} />
        </div>
      </div>

      <div
        className="pointer-events-none absolute top-1/2 z-[10] flex -translate-y-1/2 items-center isolate"
        style={{ left: phoneLeft }}
      >
        <OfferingIphoneDevice
          screenSrc={centerScreenSrc}
          screenAlt={centerScreenAlt}
          screen={centerScreen}
          frameSrc={deviceFrameSrc}
          frameSpec={frameSpec}
        />
      </div>

      <header className="absolute left-0 right-0 top-0 z-[20] px-[60px] pb-[16px] pt-[40px]">
        <div className="flex w-full items-center justify-between gap-6">
          <MonoLabel className="min-w-0 shrink">{label}</MonoLabel>
          <div className="shrink-0">
            <Logo variant="secondary" size="small" />
          </div>
        </div>
        <div className="mt-[16px] min-w-0" style={{ maxWidth: Math.max(0, titleBlockMaxW) }}>
          <SectionTitle className="leading-[1.1]">{title}</SectionTitle>
          {subtitle ? (
            <div className="mt-[6px]">
              <Heading2>{subtitle}</Heading2>
            </div>
          ) : null}
          {/* Espace réservé : le Divider réel est dans le calque z-[4] ci-dessus */}
          <div className="mt-[12px] h-0" aria-hidden />
        </div>
      </header>
    </div>
  );
}
