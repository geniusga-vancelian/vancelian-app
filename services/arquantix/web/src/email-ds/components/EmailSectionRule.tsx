import * as React from 'react'
import { emailDsColors } from '@/email-ds/tokens'

export function EmailSectionRule({ style }: { style?: React.CSSProperties }) {
  return (
    <div
      style={{
        height: 1,
        background: emailDsColors.borderNavy20,
        width: '100%',
        margin: 0,
        ...style,
      }}
    />
  )
}
