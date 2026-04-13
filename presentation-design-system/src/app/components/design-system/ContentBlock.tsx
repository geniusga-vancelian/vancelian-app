import { ReactNode } from 'react';

interface ContentBlockProps {
  children: ReactNode;
  className?: string;
}

export function ContentBlock({ children, className = '' }: ContentBlockProps) {
  return (
    <div className={`flex flex-col gap-[28px] ${className}`}>
      {children}
    </div>
  );
}

interface SectionProps {
  title: string;
  content: ReactNode;
}

export function Section({ title, content }: SectionProps) {
  return (
    <div className="flex flex-col gap-[20px]">
      <h3 className="font-['Geist:SemiBold',sans-serif] text-[36px] font-semibold leading-[1.15] text-[#1e1c1b]">
        {title}
      </h3>
      <div className="font-['Geist:Regular',sans-serif] text-[22px] font-normal leading-[1.45] tracking-[-0.5px] text-[#1e1c1b]">
        {content}
      </div>
    </div>
  );
}
