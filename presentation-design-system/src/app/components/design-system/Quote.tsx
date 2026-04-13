import svgPaths from "../../../imports/svg-y785mg5egn";

interface QuoteProps {
  children: React.ReactNode;
  attribution?: string;
  role?: string;
  iconColor?: string;
}

function QuoteIcon({ color = '#4F46E5' }: { color?: string }) {
  return (
    <div className="h-[30px] relative shrink-0 w-[43px]">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 43 30">
        <g clipPath="url(#clip0_quote)" id="Layer_1">
          <path d={svgPaths.p15cb14f0} fill={color} />
          <path d={svgPaths.p21001240} fill={color} />
        </g>
        <defs>
          <clipPath id="clip0_quote">
            <rect fill="white" height="30" width="43" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

export function Quote({ children, attribution, role, iconColor }: QuoteProps) {
  return (
    <div className="flex flex-col gap-[30px] w-full">
      <div className="flex flex-col gap-[15px]">
        <QuoteIcon color={iconColor} />
        <blockquote className="font-['Merriweather:Italic',sans-serif] italic leading-[1.2] text-[#1e1c1b] text-[40px]">
          {children}
        </blockquote>
      </div>
      {attribution && (
        <div className="flex justify-end">
          <div className="text-right">
            <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[24px] mb-1">
              {attribution}
            </p>
            {role && (
              <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[#8a8a8a] text-[18px]">
                {role}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
