import { FigmaBodyText } from '../atoms/body-text'
import { FigmaSectionTitle } from '../atoms/section-title'

interface FigmaSimpleHeroProps {
  title: string
  description: string
  backgroundColor?: string
  textColor?: string
}

/** Hero texte seul (module About Figma) — sans média ; distinct du hero pleine page CMS (`SectionHero`). */
export function FigmaSimpleHero({
  title,
  description,
  backgroundColor = 'white',
  textColor = 'black',
}: FigmaSimpleHeroProps) {
  return (
    <div
      className="content-stretch flex items-start justify-center pb-[64px] pt-[128px] px-[64px] relative shrink-0 w-full"
      style={{ backgroundColor }}
    >
      <div className="content-stretch flex flex-col gap-[30px] items-center not-italic relative shrink-0 text-center w-full max-w-[1152px]">
        <FigmaSectionTitle size="large" align="center" color={textColor}>
          {title}
        </FigmaSectionTitle>
        <div className="w-full max-w-[746px]">
          <FigmaBodyText size="large" weight="roman" color={textColor} align="center">
            {description}
          </FigmaBodyText>
        </div>
      </div>
    </div>
  )
}
