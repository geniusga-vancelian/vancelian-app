import svgPaths from "../../../imports/svg-y785mg5egn";

interface ArrowProps {
  color?: string;
  className?: string;
}

export function Arrow({ color = '#1E1C1B', className = '' }: ArrowProps) {
  return (
    <div className={`flex h-[0.333px] items-center justify-center relative shrink-0 w-[34px] ${className}`}>
      <div className="flex-none rotate-[-0.56deg]">
        <div className="h-0 relative w-[34.002px]">
          <div className="absolute inset-[-7.36px_-2.94%_-7.36px_0]">
            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 35.0016 14.7279">
              <path d={svgPaths.p34bcc570} fill={color} id="Arrow" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
