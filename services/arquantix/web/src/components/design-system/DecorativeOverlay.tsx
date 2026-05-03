import svgPaths from './imports/Arguments/svg-4rcxs0pptu';

interface DecorativeOverlayProps {
  variant: 'right-bottom' | 'left-top';
}

/**
 * DecorativeOverlay - Superposition SVG décorative pour les images
 * Utilisé dans le design system Arquantix
 */
export function DecorativeOverlay({ variant }: DecorativeOverlayProps) {
  if (variant === 'right-bottom') {
    return (
      <div className="absolute flex inset-[-75.05%_-43.86%_-88.49%_-50.63%] items-center justify-center" style={{ containerType: "size" }}>
        <div className="flex-none h-[hypot(-16.1225cqw,-16.2687cqh)] rotate-[135.15deg] w-[hypot(-83.8775cqw,83.7313cqh)]">
          <div className="relative size-full">
            <div className="absolute inset-[0_-0.28%_-0.7%_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1255.24 243.589">
                <g>
                  <path d={svgPaths.pba50e00} stroke="var(--stroke-0, white)" strokeMiterlimit="10" strokeWidth="3" />
                  <path d={svgPaths.p25dfc400} stroke="var(--stroke-0, white)" strokeMiterlimit="10" strokeWidth="3" />
                </g>
              </svg>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // left-top variant
  return (
    <div className="absolute flex inset-[-60.25%_-62.67%_-48.58%_-58.82%] items-center justify-center" style={{ containerType: "size" }}>
      <div className="-rotate-30 -scale-x-100 flex-none h-[hypot(10.0375cqw,25.0782cqh)] w-[hypot(-89.9625cqw,74.9218cqh)]">
        <div className="relative size-full">
          <div className="absolute inset-[0_-0.28%_-0.7%_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1255.24 243.589">
              <g>
                <path d={svgPaths.pba50e00} stroke="var(--stroke-0, white)" strokeMiterlimit="10" strokeWidth="3" />
                <path d={svgPaths.p7d05480} stroke="var(--stroke-0, white)" strokeMiterlimit="10" strokeWidth="3" />
              </g>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
