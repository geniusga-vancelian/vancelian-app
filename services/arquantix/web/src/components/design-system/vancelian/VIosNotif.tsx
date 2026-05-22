'use client'

import * as React from 'react'
import { Logo } from '@/components/ui/Logo'

export interface VIosNotifProps {
  appName?: string
  message?: string
  timeLabel?: string
}

/** Notification iOS glassmorphism (DS `ios-notif`). */
export function VIosNotif({
  appName = 'Vancelian',
  message,
  timeLabel = 'maintenant',
}: VIosNotifProps) {
  if (!message?.trim()) return null
  return (
    <aside
      className="grid w-full max-w-[380px] grid-cols-[32px_1fr_auto] items-center gap-2.5 rounded-2xl border border-white/[0.22] bg-white/[0.12] px-3.5 py-2.5 text-left text-white shadow-[0_12px_32px_rgba(20,18,8,0.22)] backdrop-blur-[40px] backdrop-saturate-[180%]"
      role="status"
      aria-label={`Notification ${appName}`}
    >
      <div
        className="flex h-8 w-8 items-center justify-center rounded-lg bg-v-fg"
        aria-hidden
      >
        <Logo lockup="icon" color="white" className="h-5 w-5" alt="" />
      </div>
      <div className="min-w-0">
        <p className="m-0 truncate font-ui text-[13px] font-semibold leading-[1.25]">{appName}</p>
        <p className="m-0 truncate font-ui text-[13px] font-normal leading-[1.3] text-white/90">
          {message}
        </p>
      </div>
      <span className="self-start pt-0.5 font-ui text-[11px] font-medium leading-[1.2] text-white/70 whitespace-nowrap">
        {timeLabel}
      </span>
    </aside>
  )
}
