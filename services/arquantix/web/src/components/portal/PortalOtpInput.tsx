'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

type Props = {
  value: string
  onChange: (code: string) => void
  disabled?: boolean
  /** Pulse séquentiel des cases (vérification / envoi en cours). */
  loading?: boolean
  autoFocus?: boolean
  className?: string
}

/** Saisie OTP 6 chiffres — alignée sur le bloc mobile `AppOtpInput`. */
export function PortalOtpInput({
  value,
  onChange,
  disabled = false,
  loading = false,
  autoFocus = false,
  className,
}: Props) {
  const inputsRef = React.useRef<Array<HTMLInputElement | null>>([])
  const digits = value.padEnd(6, ' ').slice(0, 6).split('')
  const isLocked = disabled || loading

  const commit = (next: string) => {
    onChange(next.replace(/\D/g, '').slice(0, 6))
  }

  const focusAt = (index: number) => {
    inputsRef.current[index]?.focus()
    inputsRef.current[index]?.select()
  }

  return (
    <div
      className={cn('flex justify-center gap-2 sm:gap-3', className)}
      aria-busy={loading || undefined}
      aria-live={loading ? 'polite' : undefined}
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => {
            inputsRef.current[index] = el
          }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          disabled={isLocked}
          autoFocus={autoFocus && index === 0}
          value={digit.trim()}
          aria-label={`Digit ${index + 1}`}
          style={loading ? { animationDelay: `${index * 0.12}s` } : undefined}
          className={cn(
            'h-14 w-11 rounded-v-card border border-v-fg-20 bg-white text-center',
            'font-ui text-[22px] font-semibold text-v-fg',
            'focus:border-v-fg focus:outline-none focus:ring-2 focus:ring-v-fg/10',
            'sm:h-16 sm:w-12',
            loading
              ? 'portal-otp-cell-loading cursor-wait'
              : 'disabled:cursor-not-allowed disabled:opacity-50',
          )}
          onChange={(e) => {
            const char = e.target.value.replace(/\D/g, '').slice(-1)
            const arr = value.padEnd(6, ' ').slice(0, 6).split('')
            arr[index] = char || ' '
            const joined = arr.join('').replace(/\s/g, '')
            commit(joined)
            if (char && index < 5) focusAt(index + 1)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Backspace' && !digit.trim() && index > 0) {
              focusAt(index - 1)
            }
          }}
          onPaste={(e) => {
            e.preventDefault()
            const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
            if (!pasted) return
            commit(pasted)
            focusAt(Math.min(pasted.length, 5))
          }}
        />
      ))}
    </div>
  )
}
