'use client'

import { useState } from 'react'
import { api } from '@/lib/strapi'

export default function EnContactPage() {
  const [formData, setFormData] = useState({ name: '', email: '', message: '' })
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    try {
      await api.submitContact(formData)
      setStatus('success')
      setFormData({ name: '', email: '', message: '' })
    } catch (error) {
      console.error('Error submitting contact:', error)
      setStatus('error')
    }
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-16 max-w-2xl">
        <h1 className="text-4xl font-bold text-slate-900 mb-8">Contact</h1>
        
        {status === 'success' && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800">Message sent successfully!</p>
          </div>
        )}

        {status === 'error' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800">Error sending message. Please try again.</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-2">
              Name
            </label>
            <input
              type="text"
              id="name"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
              Email
            </label>
            <input
              type="email"
              id="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
            />
          </div>

          <div>
            <label htmlFor="message" className="block text-sm font-medium text-slate-700 mb-2">
              Message
            </label>
            <textarea
              id="message"
              required
              rows={6}
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-slate-500 focus:border-slate-500"
            />
          </div>

          <button
            type="submit"
            disabled={status === 'loading'}
            className="w-full px-6 py-3 bg-slate-900 text-white rounded-md hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'loading' ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </main>
  )
}
