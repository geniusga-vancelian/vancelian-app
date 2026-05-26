import * as React from 'react'
import { cn } from '@/lib/utils'

const variantClass = {
  primary: 'btn--primary',
  secondary: 'btn--secondary',
  tertiary: 'btn--tertiary',
  ghost: 'btn--ghost',
  link: 'btn--link',
  destructive: 'btn--destructive',
} as const

const sizeClass = {
  xs: 'btn--xs',
  sm: 'btn--sm',
  md: '',
  lg: 'btn--lg',
} as const

export type AppButtonVariant = keyof typeof variantClass
export type AppButtonSize = keyof typeof sizeClass

export interface AppButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: AppButtonVariant
  size?: AppButtonSize
  /** Bouton rectangle 8px (FAB group, toolbars). */
  rect?: boolean
  children: React.ReactNode
}

/** Bouton webapp — classes `.btn` du handoff (pill par défaut). */
export function AppButton({
  variant = 'primary',
  size = 'md',
  rect = false,
  className,
  type = 'button',
  children,
  disabled,
  ...rest
}: AppButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={cn(
        'btn',
        variantClass[variant],
        sizeClass[size],
        rect && 'btn--rect',
        disabled && 'btn--disabled',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  )
}
