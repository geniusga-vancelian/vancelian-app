import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2, BodyLarge } from "../design-system/Typography";

interface ComparisonColumn {
  title: string;
  items: Array<{
    label: string;
    value: ReactNode;
    highlight?: boolean;
  }>;
  variant?: 'default' | 'highlight';
}

interface ComparisonSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  columns: ComparisonColumn[];
  footerText?: string;
}

export function ComparisonSlide({
  label,
  title,
  subtitle,
  columns,
  footerText = "Confidential Document"
}: ComparisonSlideProps) {
  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[36px] pt-[20px]">
        <div className="grid grid-cols-3 gap-[28px]">
          {columns.map((column, colIndex) => (
            <div 
              key={colIndex}
              className={`rounded-[16px] p-[28px] ${
                column.variant === 'highlight' 
                  ? 'bg-[#4F46E5] text-white' 
                  : 'bg-[#f2f2f2]'
              }`}
            >
              {/* Column Title */}
              <h3 className={`mb-[20px] border-b pb-[16px] text-center font-['Geist:Bold',sans-serif] text-[30px] font-bold leading-[1.15] ${
                column.variant === 'highlight' 
                  ? 'text-white border-white/30' 
                  : 'text-[#1e1c1b] border-[#1e1c1b]/20'
              }`}>
                {column.title}
              </h3>

              {/* Items */}
              <div className="space-y-[16px]">
                {column.items.map((item, itemIndex) => (
                  <div 
                    key={itemIndex}
                    className={`pb-[16px] ${
                      itemIndex !== column.items.length - 1 
                        ? column.variant === 'highlight' 
                          ? 'border-b border-white/20' 
                          : 'border-b border-[#1e1c1b]/10'
                        : ''
                    }`}
                  >
                    <p className={`font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[14px] uppercase tracking-[1px] mb-[8px] ${
                      column.variant === 'highlight' 
                        ? 'text-white/70' 
                        : 'text-[#8a8a8a]'
                    }`}>
                      {item.label}
                    </p>
                    <div className={`font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[24px] ${
                      column.variant === 'highlight' 
                        ? 'text-white' 
                        : item.highlight 
                          ? 'text-[#4F46E5]'
                          : 'text-[#1e1c1b]'
                    }`}>
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
