import type { ReactNode } from 'react';
import { Caption } from "./Typography";
import { Divider } from "./Divider";

interface SlideFooterProps {
  text?: string;
  showDivider?: boolean;
  /** Ex. astérisque décoratif à gauche ; le texte passe à droite (style slide portrait équipe). */
  leading?: ReactNode;
}

export function SlideFooter({ text = "Confidential Document", showDivider = true, leading }: SlideFooterProps) {
  return (
    <div className="absolute bottom-0 left-0 flex h-[40px] w-full items-center px-[60px] py-[20px]">
      {showDivider ? (
        <div className="absolute left-[60px] right-[60px] top-0">
          <Divider />
        </div>
      ) : null}
      <div
        className={`absolute bottom-[25px] left-[60px] right-[60px] flex items-center ${
          leading ? 'justify-between' : 'justify-start'
        }`}
      >
        {leading ? <span className="text-[#8a8a8a]">{leading}</span> : null}
        <Caption className={leading ? 'text-right' : ''}>{text}</Caption>
      </div>
    </div>
  );
}
