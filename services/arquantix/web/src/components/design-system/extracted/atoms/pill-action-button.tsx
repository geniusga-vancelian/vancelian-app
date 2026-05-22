interface PillActionButtonProps {
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'outlined'
  onClick?: () => void
  className?: string
}

/** Bouton pilule marketing (export Figma). Pour formulaires / admin, préférer `components/ui/button`. */
export function PillActionButton({
  children,
  variant = 'primary',
  onClick,
  className = '',
}: PillActionButtonProps) {
  const baseClasses =
    'content-stretch flex items-center justify-center px-[24px] py-[12px] relative rounded-[100px] shrink-0 transition-all duration-200 cursor-pointer'

  const variantClasses = {
    primary: 'bg-black hover:bg-gray-800',
    secondary: 'bg-transparent hover:bg-gray-100',
    outlined: 'bg-transparent border border-solid border-[#f3f3f3] hover:bg-white/10',
  }

  const textColorClasses = {
    primary: 'text-white',
    secondary: 'text-black',
    outlined: 'text-[#f3f3f3]',
  }

  return (
    <button type="button" className={`${baseClasses} ${variantClasses[variant]} ${className}`} onClick={onClick}>
      <span
        className={`font-ui font-semibold leading-none not-italic relative shrink-0 text-[16px] whitespace-nowrap ${textColorClasses[variant]}`}
      >
        {children}
      </span>
    </button>
  )
}
