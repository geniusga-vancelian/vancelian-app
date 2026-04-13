import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Arrow } from "../design-system/Arrow";
import { Heading2 } from "../design-system/Typography";
import { FeatureCard, StackedFeatureCard } from "../design-system/Card";

interface InfrastructureSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  features: Array<{
    type: 'single' | 'stacked';
    title: string;
    description: string | string[];
    variant?: 'white' | 'light' | 'medium';
  }>;
  footerText?: string;
}

export function InfrastructureSlide({
  label,
  title,
  subtitle,
  features,
  footerText = "Confidential Document"
}: InfrastructureSlideProps) {
  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && (
          <>
            <Arrow />
            <Heading2>{subtitle}</Heading2>
          </>
        )}
      />

      <div className="absolute left-[822px] top-[268px] w-[1038px] flex flex-col overflow-clip rounded-[10px]">
        {features.map((feature, index) => (
          <div key={index}>
            {feature.type === 'single' ? (
              <FeatureCard 
                title={feature.title}
                description={feature.description as string}
                variant={feature.variant || 'light'}
              />
            ) : (
              <StackedFeatureCard 
                title={feature.title}
                items={feature.description as string[]}
                variant={feature.variant || 'light'}
              />
            )}
          </div>
        ))}
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
