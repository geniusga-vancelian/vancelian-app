import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2, BodyLarge } from "../design-system/Typography";

interface RoadmapItem {
  phase: string;
  quarter: string;
  title: string;
  items: string[];
  status?: 'completed' | 'in-progress' | 'planned';
}

interface RoadmapSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  roadmapItems: RoadmapItem[];
  footerText?: string;
}

export function RoadmapSlide({
  label,
  title,
  subtitle,
  roadmapItems,
  footerText = "Confidential Document"
}: RoadmapSlideProps) {
  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'in-progress':
        return 'bg-[#4F46E5]';
      case 'planned':
        return 'bg-gray-300';
      default:
        return 'bg-gray-300';
    }
  };

  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[32px] pt-[16px]">
        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute bottom-0 left-[20px] top-0 w-[2px] bg-[#4F46E5] opacity-30" />

          <div className="space-y-[28px]">
            {roadmapItems.map((item, index) => (
              <div key={index} className="relative pl-[64px]">
                {/* Status Dot */}
                <div className={`absolute left-[11px] top-[8px] w-[18px] h-[18px] rounded-full ${getStatusColor(item.status)}`} />

                <div className="rounded-[12px] bg-[#f2f2f2] p-[24px]">
                  <div className="mb-[12px] flex items-start justify-between">
                    <div>
                      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#4F46E5] text-[18px] uppercase tracking-[2px] mb-[8px]">
                        {item.phase}
                      </p>
                      <Heading2>{item.title}</Heading2>
                    </div>
                    <div className="text-right">
                      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[#8a8a8a] text-[24px]">
                        {item.quarter}
                      </p>
                    </div>
                  </div>

                  <ul className="mt-[16px] grid grid-cols-2 gap-x-[40px] gap-y-[8px]">
                    {item.items.map((listItem, idx) => (
                      <li key={idx} className="flex items-start gap-[12px]">
                        <span className="text-[#4F46E5] mt-[8px]">→</span>
                        <BodyLarge className="text-[18px] leading-[1.35]">{listItem}</BodyLarge>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
