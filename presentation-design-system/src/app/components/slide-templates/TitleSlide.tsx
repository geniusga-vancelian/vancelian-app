import { Logo } from "../design-system/Logo";
import { DisplayTitle, Label } from "../design-system/Typography";
import { Divider } from "../design-system/Divider";
import { SlideFooter } from "../design-system/SlideFooter";
import imgTitre from '../../../assets/861170a11f4a4fe1209a5d7dcb40b266cb55f996.png';

interface TitleSlideProps {
  label?: string;
  title: string;
  subtitle?: string;
  backgroundImage?: string;
  footerText?: string;
}

export function TitleSlide({ 
  label = "Pitch Deck", 
  title, 
  subtitle,
  backgroundImage = imgTitre,
  footerText = "Confidential Document"
}: TitleSlideProps) {
  return (
    <div className="relative h-[1080px] w-[1920px] overflow-clip">
      {backgroundImage && (
        <img 
          alt="" 
          className="absolute inset-0 max-w-none object-cover pointer-events-none size-full" 
          src={backgroundImage} 
        />
      )}
      <div className="relative flex flex-col items-start justify-between p-[120px] size-full">
        <Logo variant="primary" size="large" />
        
        <div className="flex w-[912px] flex-col">
          {label ? <Label>{label}</Label> : null}
          <DisplayTitle className="mt-[16px] whitespace-pre-wrap leading-[1.1]">
            {title}
          </DisplayTitle>
          {subtitle ? (
            <p className="mt-[10px] font-['Geist:Regular',sans-serif] text-[32px] font-normal leading-[1.35] text-[#1e1c1b]">
              {subtitle}
            </p>
          ) : null}
          <div className="mt-[12px]">
            <Divider />
          </div>
        </div>
      </div>
      
      <SlideFooter text={footerText} showDivider={false} />
    </div>
  );
}
