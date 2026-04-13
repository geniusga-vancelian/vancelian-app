import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2, BodyLarge } from "../design-system/Typography";

interface Feature {
  icon?: ReactNode;
  title: string;
  description: string;
}

interface FeatureGridSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  features: Feature[];
  columns?: 2 | 3 | 4;
  footerText?: string;
}

export function FeatureGridSlide({
  label,
  title,
  subtitle,
  features,
  columns = 3,
  footerText = "Confidential Document"
}: FeatureGridSlideProps) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4'
  };

  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[36px] pt-[20px]">
        <div className={`grid ${gridCols[columns]} gap-x-[28px] gap-y-[24px]`}>
          {features.map((feature, index) => (
            <div 
              key={index}
              className="flex flex-col gap-[18px] rounded-[16px] bg-[#f2f2f2] p-[28px] transition-colors hover:bg-[rgba(79,70,229,0.05)]"
            >
              {/* Icon */}
              {feature.icon && (
                <div className="w-[96px] h-[96px] bg-white rounded-[12px] flex items-center justify-center">
                  {feature.icon}
                </div>
              )}

              {/* Title */}
              <h3 className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[28px]">
                {feature.title}
              </h3>

              {/* Description */}
              <BodyLarge className="text-[17px] leading-[1.4] text-[#8a8a8a]">
                {feature.description}
              </BodyLarge>
            </div>
          ))}
        </div>
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
