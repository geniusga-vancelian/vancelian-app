interface DividerProps {
  /** accent : indigo DS · warm : sable · coral : offre / trading · primary : ligne indigo */
  variant?: 'primary' | 'accent' | 'warm' | 'coral';
  accentWidth?: number;
  className?: string;
}

const WARM = '#B8956E';
const WARM_MUTED = '#B8956E';
const CORAL = '#E85D4C';
const CORAL_MUTED = '#E85D4C';

export function Divider({ variant = 'accent', accentWidth = 53, className = '' }: DividerProps) {
  if (variant === 'primary') {
    return (
      <div className={`w-full h-px bg-[#4F46E5] opacity-30 ${className}`} />
    );
  }

  if (variant === 'warm') {
    return (
      <div className={`flex w-full items-start ${className}`}>
        <div className="relative h-0 shrink-0" style={{ width: accentWidth }}>
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${accentWidth} 1`}>
              <line stroke={WARM} strokeWidth={1} x2={accentWidth} y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="relative h-0 min-h-px min-w-px flex-1">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${1800 - accentWidth} 1`}>
              <line opacity="0.45" stroke={WARM_MUTED} x2={1800 - accentWidth} y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'coral') {
    return (
      <div className={`flex w-full items-start ${className}`}>
        <div className="relative h-0 shrink-0" style={{ width: accentWidth }}>
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${accentWidth} 1`}>
              <line stroke={CORAL} strokeWidth={1} x2={accentWidth} y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
        <div className="relative h-0 min-h-px min-w-px flex-1">
          <div className="absolute inset-[-1px_0_0_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${1800 - accentWidth} 1`}>
              <line opacity="0.5" stroke={CORAL_MUTED} x2={1800 - accentWidth} y1="0.5" y2="0.5" />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-start w-full ${className}`}>
      <div className="h-0 relative shrink-0" style={{ width: accentWidth }}>
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${accentWidth} 1`}>
            <line stroke="#4F46E5" x2={accentWidth} y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
      <div className="flex-1 h-0 min-h-px min-w-px relative">
        <div className="absolute inset-[-1px_0_0_0]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox={`0 0 ${1800 - accentWidth} 1`}>
            <line opacity="0.3" stroke="#4F46E5" x2={1800 - accentWidth} y1="0.5" y2="0.5" />
          </svg>
        </div>
      </div>
    </div>
  );
}
