import { ParagraphLargeBold } from '../atoms/paragraph-large-bold'
import { Paragraph } from '../atoms/paragraph'
import { cn } from '@/lib/utils'

interface FigmaTestimonialCardProps {
  author: string
  role: string
  content: string
  avatar?: string
  backgroundColor?: string
  className?: string
}

/** Carte témoignage / membre — espacements Figma 24px, avatar 48×48 coins arrondis, typo Avenir. */
export function FigmaTestimonialCard({
  author,
  role,
  content,
  avatar,
  backgroundColor = '#f4f4f4',
  className,
}: FigmaTestimonialCardProps) {
  return (
    <div
      className={cn('relative w-full min-w-0 rounded-[10px]', className)}
      style={{ backgroundColor }}
    >
      <div className="flex flex-col gap-6 p-6">
        <div className="flex w-full items-start gap-3">
          {avatar ? (
            <div className="h-12 w-12 shrink-0 overflow-hidden rounded-[10px]">
              <img
                alt={author}
                className="pointer-events-none size-full max-w-none object-cover"
                src={avatar}
              />
            </div>
          ) : null}
          <div className="flex min-w-0 flex-1 flex-col items-start gap-0">
            <ParagraphLargeBold className="mb-0">{author}</ParagraphLargeBold>
            <Paragraph color="#62656e" className="m-0">
              {role}
            </Paragraph>
          </div>
        </div>

        <hr className="w-full border-0 border-t border-[#62656E]/30" />

        <Paragraph className="m-0 text-left">{content}</Paragraph>
      </div>
    </div>
  )
}
