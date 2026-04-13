import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";

interface CenteredContentSlideProps {
  label: string;
  title: string;
  subtitle?: ReactNode;
  leftContent?: ReactNode;
  rightContent?: ReactNode;
  centerImage?: ReactNode;
  backgroundImage?: string;
  footerText?: string;
}

export function CenteredContentSlide({
  label,
  title,
  subtitle,
  leftContent,
  rightContent,
  centerImage,
  backgroundImage,
  footerText = "Confidential Document"
}: CenteredContentSlideProps) {
  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip flex">
      {/* Left Section */}
      {leftContent && (
        <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-white">
          <SlideHeader
            label={label}
            title={title}
            subtitle={subtitle}
            showLogo={false}
          />
          <div className="flex min-h-0 flex-1 flex-col justify-center pl-[120px] pr-[60px] pb-[72px] pt-[8px]">
            {leftContent}
          </div>
        </div>
      )}

      {/* Right Section */}
      {rightContent && (
        <div className="relative flex h-full min-h-0 flex-1 flex-col overflow-hidden">
          {backgroundImage && (
            <>
              <img 
                alt="" 
                className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" 
                src={backgroundImage} 
              />
              <div className="absolute inset-[-50.56%_-57.61%_-16.3%_-30.1%]">
                <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 1802.03 1802.05">
                  <defs>
                    <linearGradient gradientUnits="userSpaceOnUse" id="paint0_linear_gradient" x1="7063.89" x2="901.012" y1="-1716.96" y2="1802.05">
                      <stop stopColor="white" />
                      <stop offset="1" stopColor="#DDDDDD" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </>
          )}
          <div className="relative flex min-h-0 flex-1 flex-col justify-center pl-[60px] pr-[120px] pb-[72px] pt-[8px]">
            {rightContent}
          </div>
        </div>
      )}

      {/* Center Image */}
      {centerImage && (
        <div className="absolute left-1/2 -translate-x-1/2 top-[276px] h-[944px] w-[446px]">
          {centerImage}
        </div>
      )}

      <SlideFooter text={footerText} />
    </div>
  );
}
