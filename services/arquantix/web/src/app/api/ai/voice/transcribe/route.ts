import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { openai } from '@/lib/openai/client'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 })
    }

    // Validate file type
    const allowedTypes = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-m4a']
    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: `Invalid file type. Allowed: ${allowedTypes.join(', ')}` },
        { status: 400 }
      )
    }

    // Check file size (max 15MB)
    const maxSize = 15 * 1024 * 1024
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: 'File too large (max 15MB)' },
        { status: 400 }
      )
    }

    // Convert File to a format OpenAI SDK can use
    // The OpenAI SDK accepts File, Blob, or a stream
    // In Next.js server environment, we can pass the File directly
    // or convert to a Blob if needed
    const arrayBuffer = await file.arrayBuffer()
    const blob = new Blob([arrayBuffer], { type: file.type })
    
    // Create a File object for OpenAI (File constructor works in Node.js 18+)
    const fileForOpenAI = new File([blob], file.name || 'audio.webm', { type: file.type })

    // Call OpenAI Whisper API
    try {
      const transcription = await openai.audio.transcriptions.create({
        file: fileForOpenAI,
        model: 'whisper-1',
      })

      const transcript = transcription.text

      if (!transcript) {
        return NextResponse.json(
          { error: 'No transcript returned' },
          { status: 500 }
        )
      }

      return NextResponse.json({ transcript })
    } catch (openaiError: any) {
      console.error('OpenAI transcription error:', openaiError)
      const errorMessage = openaiError?.error?.message || 'Failed to transcribe audio'
      return NextResponse.json(
        { error: errorMessage },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('AI Voice transcribe error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
