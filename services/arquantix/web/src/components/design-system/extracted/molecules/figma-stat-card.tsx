import { FigmaBodyText } from '../atoms/body-text'
import { FigmaSectionTitle } from '../atoms/section-title'

interface FigmaStatCardProps {
  value: string
  label: string
  showBorder?: boolean
  align?: 'left' | 'center'
}

/**
 * Carte stat Figma (titres + corps). Distinct de `ds-hero/stat-card` (autre mise en page).
 */
export function FigmaStatCard({
  value,
  label,
  showBorder = false,
  align = 'left',
}: FigmaStatCardProps) {
  const centered = align === 'center'
  return (
    <div className="relative h-full min-h-px min-w-0 flex-[1_1_0] basis-0">
      {showBorder && (
        <div
          aria-hidden="true"
          className="absolute border-[#f3f3f3] border-l border-solid inset-0 pointer-events-none"
        />
      )}
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center px-[20px] py-[30px] relative size-full">
          <div className="content-stretch flex flex-[1_0_0] items-center min-h-px min-w-px relative">
            <div className="content-stretch flex flex-[1_0_0] flex-col min-h-px min-w-px relative">
              <div
                className={`content-stretch flex flex-col gap-[10px] not-italic relative shrink-0 text-[#62656e] w-full ${
                  centered ? 'items-center' : 'items-start'
                }`}
              >
                <FigmaSectionTitle size="small" align={centered ? 'center' : 'left'} color="#62656e">
                  {value}
                </FigmaSectionTitle>
                <FigmaBodyText
                  size="small"
                  weight="book"
                  color="#62656e"
                  align={centered ? 'center' : 'left'}
                >
                  {label}
                </FigmaBodyText>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
