import { NextResponse } from 'next/server'
import { clearPortalSessionCookies } from '@/lib/portal/portalSession'

export async function POST() {
  const res = NextResponse.json({ ok: true })
  clearPortalSessionCookies(res)
  return res
}
