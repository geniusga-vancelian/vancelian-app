'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { portalProfileWalletsRoute } from '@/lib/portal/portalRouting'

/** Redirige vers la section wallets du profil. */
export default function PortalMyWalletsPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace(portalProfileWalletsRoute())
  }, [router])

  return null
}
