import { MediaTextSection } from '@/components/design-system/MediaTextSection'

export interface SectionMediaTextProps {
  /** Surtitre / pastille au-dessus du titre (CMS, traduisible). */
  eyebrow?: string
  title?: string
  description?: string
  imageMediaUrl?: string
  videoMediaUrl?: string
  imageMediaAlt?: string | null
  mediaRight?: boolean
}

export function SectionMediaText({
  eyebrow,
  title = '',
  description = '',
  imageMediaUrl,
  videoMediaUrl,
  imageMediaAlt,
  mediaRight = false,
}: SectionMediaTextProps) {
  return (
    <MediaTextSection
      eyebrow={eyebrow}
      title={title}
      description={description}
      imageSrc={imageMediaUrl}
      videoSrc={videoMediaUrl}
      imageAlt={imageMediaAlt}
      mediaRight={mediaRight === true}
    />
  )
}
