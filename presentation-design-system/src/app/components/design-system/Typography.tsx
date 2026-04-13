interface TypographyProps {
  children: React.ReactNode;
  className?: string;
}

export function DisplayTitle({ children, className = '' }: TypographyProps) {
  return (
    <h1 className={`font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] text-[#1e1c1b] text-[96px] ${className}`}>
      {children}
    </h1>
  );
}

export function SectionTitle({ children, className = '' }: TypographyProps) {
  return (
    <h2 className={`font-['Geist:ExtraLight',sans-serif] font-extralight leading-[1.2] text-[#1e1c1b] text-[60px] ${className}`}>
      {children}
    </h2>
  );
}

export function Heading1({ children, className = '' }: TypographyProps) {
  return (
    <h3 className={`font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[#1e1c1b] text-[40px] ${className}`}>
      {children}
    </h3>
  );
}

export function Heading2({ children, className = '' }: TypographyProps) {
  return (
    <h4 className={`font-['Geist:Medium',sans-serif] font-medium leading-[1.2] text-[#1e1c1b] text-[32px] ${className}`}>
      {children}
    </h4>
  );
}

export function BodyLarge({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[#1e1c1b] text-[24px] tracking-[-1px] ${className}`}>
      {children}
    </p>
  );
}

export function BodyMedium({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[#1e1c1b] text-[18px] ${className}`}>
      {children}
    </p>
  );
}

export function Caption({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist:Regular',sans-serif] font-normal leading-[1.4] text-[#8a8a8a] text-[13px] ${className}`}>
      {children}
    </p>
  );
}

export function Label({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist:Light',sans-serif] font-light leading-[1.2] text-[#8a8a8a] text-[24px] tracking-[7px] uppercase ${className}`}>
      {children}
    </p>
  );
}

export function MonoLabel({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist_Mono:Light',sans-serif] font-light leading-[1.2] text-[#8a8a8a] text-[24px] uppercase ${className}`}>
      {children}
    </p>
  );
}

export function QuoteText({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Merriweather:Italic',sans-serif] italic leading-[1.2] text-[#1e1c1b] text-[40px] ${className}`}>
      {children}
    </p>
  );
}

export function Attribution({ children, className = '' }: TypographyProps) {
  return (
    <div className={`text-right ${className}`}>
      <p className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[24px]">
        {children}
      </p>
    </div>
  );
}

export function AttributionRole({ children, className = '' }: TypographyProps) {
  return (
    <p className={`font-['Geist:Regular',sans-serif] font-normal leading-[1.5] text-[#8a8a8a] text-[18px] ${className}`}>
      {children}
    </p>
  );
}
