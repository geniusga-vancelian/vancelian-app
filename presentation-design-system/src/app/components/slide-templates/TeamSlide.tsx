import { ReactNode } from 'react';
import { SlideHeader } from "../design-system/SlideHeader";
import { SlideFooter } from "../design-system/SlideFooter";
import { Heading2, BodyLarge } from "../design-system/Typography";

interface TeamMember {
  name: string;
  role: string;
  bio: string;
  image?: string;
  linkedin?: string;
}

interface TeamSlideProps {
  label: string;
  title: string;
  subtitle?: string;
  teamMembers: TeamMember[];
  layout?: '2-column' | '3-column' | '4-column';
  footerText?: string;
}

export function TeamSlide({
  label,
  title,
  subtitle,
  teamMembers,
  layout = '3-column',
  footerText = "Confidential Document"
}: TeamSlideProps) {
  const gridCols = {
    '2-column': 'grid-cols-2',
    '3-column': 'grid-cols-3',
    '4-column': 'grid-cols-4'
  };

  return (
    <div className="relative bg-white h-[1080px] w-[1920px] overflow-clip">
      <SlideHeader 
        label={label}
        title={title}
        subtitle={subtitle && <Heading2>{subtitle}</Heading2>}
      />

      <div className="px-[120px] pb-[32px] pt-[16px]">
        <div className={`grid ${gridCols[layout]} gap-x-[32px] gap-y-[24px]`}>
          {teamMembers.map((member, index) => (
            <div key={index} className="flex flex-col items-center text-center">
              {/* Avatar */}
              <div className="mb-[14px] flex h-[160px] w-[160px] items-center justify-center overflow-hidden rounded-full bg-[#f2f2f2]">
                {member.image ? (
                  <img 
                    src={member.image} 
                    alt={member.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-[48px] font-bold text-[#8a8a8a]">
                    {member.name.split(' ').map(n => n[0]).join('')}
                  </div>
                )}
              </div>

              {/* Name */}
              <h3 className="font-['Geist:Bold',sans-serif] font-bold leading-[1.2] text-[#1e1c1b] text-[28px] mb-[8px]">
                {member.name}
              </h3>

              {/* Role */}
              <p className="font-['Geist:SemiBold',sans-serif] font-semibold leading-[1.2] text-[#4F46E5] text-[18px] uppercase tracking-[1px] mb-[16px]">
                {member.role}
              </p>

              {/* Bio */}
              <BodyLarge className="text-[15px] leading-[1.35] text-[#8a8a8a]">
                {member.bio}
              </BodyLarge>

              {/* LinkedIn */}
              {member.linkedin && (
                <a 
                  href={member.linkedin}
                  className="mt-[16px] text-[#4F46E5] text-[14px] hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  LinkedIn →
                </a>
              )}
            </div>
          ))}
        </div>
      </div>

      <SlideFooter text={footerText} />
    </div>
  );
}
