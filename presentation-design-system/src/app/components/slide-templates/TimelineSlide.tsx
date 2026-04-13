import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2, BodyLarge } from "../design-system/Typography";

interface TimelineEvent {
  date: string;
  title: string;
  description: string;
  highlight?: boolean;
}

interface TimelineSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  events: TimelineEvent[];
  footerText?: string;
}

export function TimelineSlide({
  label,
  title,
  subtitle,
  events,
  footerText = "Confidential Document"
}: TimelineSlideProps) {
  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[32px] pt-[16px]">
        <div className="relative">
          {/* Horizontal Timeline Line */}
          <div className="absolute left-0 right-0 top-[36px] h-[2px] bg-[#4F46E5] opacity-30" />

          <div className="grid grid-cols-4 gap-[24px]">
            {events.map((event, index) => (
              <div key={index} className="relative">
                {/* Timeline Dot */}
                <div 
                  className={`absolute left-1/2 top-[27px] h-[18px] w-[18px] -translate-x-1/2 rounded-full ${
                    event.highlight ? 'bg-[#4F46E5]' : 'bg-gray-300'
                  }`}
                />

                <div className="pt-[68px]">
                  {/* Date */}
                  <p className="mb-[10px] text-center font-['Geist:Bold',sans-serif] text-[18px] font-bold uppercase leading-[1.2] tracking-[2px] text-[#4F46E5]">
                    {event.date}
                  </p>

                  {/* Card */}
                  <div className={`rounded-[12px] p-[18px] ${
                    event.highlight ? 'bg-[#4F46E5] text-white' : 'bg-[#f2f2f2]'
                  }`}>
                    <h3 className={`mb-[8px] font-['Geist:Bold',sans-serif] text-[19px] font-bold leading-[1.2] ${
                      event.highlight ? 'text-white' : 'text-[#1e1c1b]'
                    }`}>
                      {event.title}
                    </h3>
                    <p className={`font-['Geist:Regular',sans-serif] font-normal leading-[1.4] text-[14px] ${
                      event.highlight ? 'text-white opacity-90' : 'text-[#8a8a8a]'
                    }`}>
                      {event.description}
                    </p>
                  </div>
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
