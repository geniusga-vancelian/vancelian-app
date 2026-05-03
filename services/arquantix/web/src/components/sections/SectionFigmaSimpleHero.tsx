import { FigmaSimpleHero } from '@/components/design-system/extracted'

export interface SectionFigmaSimpleHeroProps {
  title?: string
  description?: string
  backgroundColor?: string
  textColor?: string
}

export function SectionFigmaSimpleHero({
  title = '',
  description = '',
  backgroundColor = '#ffffff',
  textColor = '#000000',
}: SectionFigmaSimpleHeroProps) {
  if (!title.trim() && !description.trim()) {
    return null
  }
  return (
    <FigmaSimpleHero
      title={title || ' '}
      description={description || ' '}
      backgroundColor={backgroundColor}
      textColor={textColor}
    />
  )
}
