import { cn } from '@/lib/utils'

interface FigmaEyebrowLabelProps {
  children: React.ReactNode
  variant?: 'outlined' | 'filled'
  color?: string
  textColor?: string
  className?: string
}

/** Libellé type « story » / catégorie (bordure fine). Distinct du `Label` Radix dans `components/ui/label`. */
export function FigmaEyebrowLabel({
  children,
  variant = 'outlined',
  color = '#f3f3f3',
  textColor = '#f3f3f3',
  className,
}: FigmaEyebrowLabelProps) {
  return (
    <div
      className={cn(
        'content-stretch relative flex shrink-0 items-center justify-center rounded-[2px] px-[4px] py-[2px]',
        className,
      )}
    >
      {variant === 'outlined' && (
        <div
          aria-hidden="true"
          className="absolute border border-solid inset-0 pointer-events-none rounded-[2px]"
          style={{ borderColor: color }}
        />
      )}
      <p
        className="font-ui font-semibold leading-none not-italic relative shrink-0 text-[14px] uppercase whitespace-nowrap"
        style={{ color: textColor }}
      >
        {children}
      </p>
    </div>
  )
}
