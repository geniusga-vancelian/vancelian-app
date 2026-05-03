import { FigmaEyebrowLabel } from '../atoms/eyebrow-label'
import { SectionTitle } from '../atoms/section-title'

interface FigmaSectionHeadingProps {
  label?: string
  title: string
  titleSize?: 'large' | 'medium' | 'small'
  titleColor?: string
  labelColor?: string
  backgroundColor?: string
}

/**
 * En-tête centré label + titre (module About Figma). Distinct de `components/ui/SectionHeader` (Tag + titre marketing).
 */
export function FigmaSectionHeading({
  label,
  title,
  titleSize = 'medium',
  titleColor = '#f3f3f3',
  labelColor = '#f3f3f3',
  backgroundColor = 'transparent',
}: FigmaSectionHeadingProps) {
  return (
    <div
      className="content-stretch flex flex-col gap-[10px] items-center relative shrink-0 w-full"
      style={{ backgroundColor }}
    >
      {label ? (
        <FigmaEyebrowLabel color={labelColor} textColor={labelColor}>
          {label}
        </FigmaEyebrowLabel>
      ) : null}
      <SectionTitle size={titleSize} align="center" color={titleColor}>
        {title}
      </SectionTitle>
    </div>
  )
}
