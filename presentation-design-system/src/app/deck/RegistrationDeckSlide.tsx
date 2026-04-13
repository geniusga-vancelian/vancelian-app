import {
  BodyLarge,
  BodyMedium,
  Heading2,
  Label,
  LabelCard,
  SlideHeader,
  SlideLayout,
  TwoColumnLayout,
} from '../components/design-system';
import type { RegistrationSlideData } from './registrationDeckContent';
import { REGISTRATION_DECK_TITLE } from './registrationDeckContent';

type Props = {
  slide: RegistrationSlideData;
  index: number;
  total: number;
};

export function RegistrationDeckSlide({ slide, index, total }: Props) {
  const footer = `Vancelian — Vue d'ensemble registration · ${index + 1} / ${total}`;

  return (
    <SlideLayout background="light" footerText={footer}>
      <TwoColumnLayout
        leftWidth="56%"
        rightWidth="44%"
        left={
          <div className="flex h-full flex-col bg-white">
            <SlideHeader label={REGISTRATION_DECK_TITLE} title={slide.sectionTitle} />
            <div className="flex min-h-0 flex-1 flex-col gap-[24px] overflow-hidden px-[60px] pb-[48px] pt-[6px]">
              <BodyLarge className="leading-[1.4]">{slide.intro}</BodyLarge>
              <Label>Informations demandées</Label>
              <div className="flex flex-col gap-[18px]">
                {slide.infoItems.map((item, i) => (
                  <div key={item.title}>
                    <Heading2 className="mb-[8px]">
                      {i + 1}. {item.title}
                    </Heading2>
                    <BodyMedium>{item.body}</BodyMedium>
                  </div>
                ))}
              </div>
            </div>
          </div>
        }
        right={
          <div className="flex h-full flex-col justify-center gap-[18px] bg-[#f2f2f2] px-[44px] py-[40px]">
            <Heading2>{slide.sidebarTitle}</Heading2>
            {slide.sidebarLead ? (
              <BodyLarge className="text-[#1e1c1b]">{slide.sidebarLead}</BodyLarge>
            ) : null}
            {slide.tags && slide.tags.length > 0 ? (
              <div className="grid grid-cols-2 gap-[12px]">
                {slide.tags.map((t) => (
                  <LabelCard key={t} label={t} variant="white" />
                ))}
              </div>
            ) : null}
            {slide.sidebarNote ? <BodyMedium>{slide.sidebarNote}</BodyMedium> : null}
            {slide.sidebarBullets.some((b) => b.text.trim()) ? (
              <ul className="flex flex-col gap-[14px]">
                {slide.sidebarBullets
                  .filter((b) => b.text.trim())
                  .map((b) => (
                    <li key={b.text} className="flex gap-[12px]">
                      {b.emoji ? (
                        <span className="shrink-0 text-[28px] leading-none" aria-hidden>
                          {b.emoji}
                        </span>
                      ) : (
                        <span className="w-[28px] shrink-0" aria-hidden />
                      )}
                      <BodyMedium className="flex-1">{b.text}</BodyMedium>
                    </li>
                  ))}
              </ul>
            ) : null}
            {slide.sidebarEmoji ? (
              <p className="mt-[8px] text-[48px] leading-none" aria-hidden>
                {slide.sidebarEmoji}
              </p>
            ) : null}
          </div>
        }
      />
    </SlideLayout>
  );
}
