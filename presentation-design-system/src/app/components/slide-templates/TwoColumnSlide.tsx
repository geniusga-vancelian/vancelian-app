import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Section } from "../design-system/ContentBlock";
import { Quote } from "../design-system/Quote";

interface TwoColumnSlideProps {
  label: string;
  title: string;
  subtitle?: ReactNode;
  sections?: Array<{
    title: string;
    content: ReactNode;
  }>;
  quote?: {
    text: ReactNode;
    attribution?: string;
    role?: string;
  };
  rightContent: ReactNode;
  backgroundColor?: 'white' | 'light';
  footerText?: string;
}

export function TwoColumnSlide({
  label,
  title,
  subtitle,
  sections = [],
  quote,
  rightContent,
  backgroundColor = 'light',
  footerText = "Confidential Document"
}: TwoColumnSlideProps) {
  const bgColor = backgroundColor === 'light' ? 'bg-[#f2f2f2]' : 'bg-white';

  return (
    <div className={`relative ${bgColor} h-[1080px] w-[1920px] overflow-clip flex`}>
      {/* Left Column */}
      <div className="bg-white flex-1 h-full overflow-clip">
        <div className="flex flex-col h-full">
          <SlideHeader 
            label={label}
            title={title}
            subtitle={subtitle}
            showLogo={false}
          />
          
          <div className="flex min-h-0 flex-1 flex-col gap-[36px] overflow-hidden px-[60px] pb-[36px]">
            {sections.map((section, index) => (
              <Section 
                key={index}
                title={section.title}
                content={section.content}
              />
            ))}
            
            {quote && (
              <Quote 
                attribution={quote.attribution}
                role={quote.role}
              >
                {quote.text}
              </Quote>
            )}
          </div>
        </div>
      </div>

      {/* Right Column */}
      <div className="w-[640px] h-full relative overflow-clip flex items-center justify-center">
        {rightContent}
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
