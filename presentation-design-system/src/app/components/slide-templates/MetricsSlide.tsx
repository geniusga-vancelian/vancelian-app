import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2 } from "../design-system/Typography";

interface Metric {
  value: string;
  label: string;
  description?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

interface MetricsSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  metrics: Metric[];
  layout?: '2x2' | '3x2' | '4-column';
  footerText?: string;
}

export function MetricsSlide({
  label,
  title,
  subtitle,
  metrics,
  layout = '4-column',
  footerText = "Confidential Document"
}: MetricsSlideProps) {
  const gridLayout = {
    '2x2': 'grid-cols-2 gap-[32px]',
    '3x2': 'grid-cols-3 gap-[28px]',
    '4-column': 'grid-cols-4 gap-[24px]',
  };

  const getTrendColor = (trend?: string) => {
    switch (trend) {
      case 'up':
        return 'text-green-500';
      case 'down':
        return 'text-red-500';
      default:
        return 'text-[#8a8a8a]';
    }
  };

  const getTrendSymbol = (trend?: string) => {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      default:
        return '';
    }
  };

  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[36px] pt-[20px]">
        <div className={`grid ${gridLayout[layout]}`}>
          {metrics.map((metric, index) => (
            <div 
              key={index} 
              className="flex min-h-[232px] flex-col items-center justify-center rounded-[16px] bg-[#f2f2f2] p-[28px] text-center"
            >
              {/* Value */}
              <p className="mb-[10px] font-['Geist:ExtraLight',sans-serif] text-[64px] font-extralight leading-[1] text-[#1e1c1b]">
                {metric.value}
              </p>

              {/* Trend */}
              {metric.trend && (
                <p className={`font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[20px] mb-[12px] ${getTrendColor(metric.trend)}`}>
                  {getTrendSymbol(metric.trend)} {metric.trendValue}
                </p>
              )}

              {/* Label */}
              <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[24px] mb-[8px]">
                {metric.label}
              </p>

              {/* Description */}
              {metric.description && (
                <p className="font-['Geist:Regular',sans-serif] font-normal leading-[1.4] text-[#8a8a8a] text-[16px]">
                  {metric.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
