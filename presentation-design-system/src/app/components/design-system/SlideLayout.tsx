import { ReactNode } from 'react';
import { SlideFooter } from './SlideFooter';

interface SlideLayoutProps {
  children: ReactNode;
  background?: 'white' | 'light';
  showFooter?: boolean;
  footerText?: string;
}

export function SlideLayout({ children, background = 'white', showFooter = true, footerText }: SlideLayoutProps) {
  const bgColor = background === 'light' ? 'bg-[#f2f2f2]' : 'bg-white';
  
  return (
    <div className={`relative ${bgColor} h-[1080px] w-[1920px] overflow-clip`}>
      {children}
      {showFooter && <SlideFooter text={footerText} />}
    </div>
  );
}

interface TwoColumnLayoutProps {
  left: ReactNode;
  right: ReactNode;
  leftWidth?: string;
  rightWidth?: string;
}

export function TwoColumnLayout({ left, right, leftWidth = '50%', rightWidth = '50%' }: TwoColumnLayoutProps) {
  return (
    <div className="flex h-full w-full">
      <div style={{ width: leftWidth }} className="h-full overflow-clip">
        {left}
      </div>
      <div style={{ width: rightWidth }} className="h-full overflow-clip">
        {right}
      </div>
    </div>
  );
}
