import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  variant?: 'white' | 'light' | 'medium';
  className?: string;
}

export function Card({ children, variant = 'white', className = '' }: CardProps) {
  const backgrounds = {
    white: 'bg-white',
    light: 'bg-[rgba(0,0,0,0.05)]',
    medium: 'bg-[rgba(0,0,0,0.1)]'
  };

  return (
    <div className={`${backgrounds[variant]} flex items-center justify-center h-[124px] rounded-[9.022px] px-[40px] ${className}`}>
      {children}
    </div>
  );
}

interface LabelCardProps {
  label: string;
  variant?: 'white' | 'light' | 'medium';
}

export function LabelCard({ label, variant = 'white' }: LabelCardProps) {
  return (
    <Card variant={variant}>
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[40px] whitespace-nowrap">
        {label}
      </p>
    </Card>
  );
}

interface FeatureCardProps {
  title: string;
  description: string;
  variant?: 'white' | 'light' | 'medium';
}

export function FeatureCard({ title, description, variant = 'white' }: FeatureCardProps) {
  const backgrounds = {
    white: 'bg-white',
    light: 'bg-[rgba(0,0,0,0.05)]',
    medium: 'bg-[rgba(0,0,0,0.1)]'
  };

  return (
    <div className={`${backgrounds[variant]} flex gap-[48px] h-[162px] items-center justify-center px-[40px] relative`}>
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[#1e1c1b] text-[28px] w-[292px]">
        {title}
      </p>
      <div className="flex-1">
        <div className="bg-white flex items-center justify-center h-[124px] rounded-[9.022px] px-[40px]">
          <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[40px] whitespace-nowrap">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}

interface StackedFeatureCardProps {
  title: string;
  items: string[];
  variant?: 'white' | 'light' | 'medium';
}

export function StackedFeatureCard({ title, items, variant = 'light' }: StackedFeatureCardProps) {
  const backgrounds = {
    white: 'bg-white',
    light: 'bg-[rgba(0,0,0,0.05)]',
    medium: 'bg-[rgba(0,0,0,0.1)]'
  };

  return (
    <div className={`${backgrounds[variant]} flex gap-[48px] h-[299px] items-center justify-center px-[40px] relative`}>
      <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[#1e1c1b] text-[28px] w-[292px]">
        {title}
      </p>
      <div className="flex-1 flex flex-col gap-[10px]">
        {items.map((item, index) => (
          <div key={index} className="bg-white flex items-center justify-center h-[124px] rounded-[9.022px] px-[40px]">
            <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[40px] whitespace-nowrap">
              {item}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
