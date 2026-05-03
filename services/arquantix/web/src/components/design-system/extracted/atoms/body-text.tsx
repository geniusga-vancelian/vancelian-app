interface BodyTextProps {
  children: React.ReactNode
  size?: 'large' | 'medium' | 'small'
  weight?: 'heavy' | 'roman' | 'book'
  color?: string
  align?: 'left' | 'center' | 'right'
}

export function FigmaBodyText({
  children,
  size = 'medium',
  weight = 'roman',
  color = 'black',
  align = 'left',
}: BodyTextProps) {
  const sizeClasses = {
    large: 'text-[18px]',
    medium: 'text-[16px]',
    small: 'text-[14px]',
  }

  const weightClasses = {
    heavy: "font-['Avenir:Heavy',sans-serif]",
    roman: "font-['Avenir:Roman',sans-serif]",
    book: "font-['Avenir:Book',sans-serif]",
  }

  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  }

  return (
    <p
      className={`${weightClasses[weight]} leading-[1.6] not-italic relative shrink-0 ${sizeClasses[size]} ${alignClasses[align]} w-full`}
      style={{ color }}
    >
      {children}
    </p>
  )
}
