'use client'

import { useState, useRef } from 'react'
import { Mic, Square } from 'lucide-react'
import { transcribeAudio } from './api'

interface VoiceRecorderProps {
  onTranscript: (transcript: string) => void
  disabled?: boolean
}

export function VoiceRecorder({ onTranscript, disabled }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })

      chunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setIsTranscribing(true)
        
        try {
          const result = await transcribeAudio(blob as File)
          onTranscript(result.transcript)
        } catch (error) {
          console.error('Transcription error:', error)
          alert('Failed to transcribe audio. Please try again.')
        } finally {
          setIsTranscribing(false)
          stream.getTracks().forEach(track => track.stop())
        }
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Failed to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  return (
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled || isTranscribing}
      className={`flex items-center justify-center w-10 h-10 rounded-full transition-colors ${
        isRecording
          ? 'bg-red-500 hover:bg-red-600 text-white'
          : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
      } ${disabled || isTranscribing ? 'opacity-50 cursor-not-allowed' : ''}`}
      title={isRecording ? 'Stop recording' : 'Start voice recording'}
    >
      {isTranscribing ? (
        <div className="w-4 h-4 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
      ) : isRecording ? (
        <Square className="w-5 h-5" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  )
}









