import { cn } from '@/lib/utils'

type CircleArrowRightIconProps = {
  className?: string
  title?: string
}

/**
 * Atome DS - Circle Arrow Right
 * Source: SVG fourni par design (22x22).
 */
export function CircleArrowRightIcon({ className, title }: CircleArrowRightIconProps) {
  return (
    <svg
      viewBox="0 0 22 22"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('h-5 w-5', className)}
      role={title ? 'img' : 'presentation'}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      <circle
        cx="11"
        cy="11"
        r="8.25"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M7.33398 11L14.6673 11M14.6673 11L11.9173 13.75M14.6673 11L11.9173 8.25"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
