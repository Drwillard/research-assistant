'use client'

import { useCallback, useEffect, useState } from 'react'
import ChatPanel from '@/components/ChatPanel'
import Sidebar from '@/components/Sidebar'
import { getDocuments, type Document, type Provider } from '@/lib/api'

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [provider, setProvider] = useState<Provider>('openai')

  useEffect(() => {
    const saved = window.localStorage.getItem('rag-provider')
    if (saved === 'openai' || saved === 'ollama') setProvider(saved)
  }, [])

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await getDocuments(provider)
      setDocuments(docs)
    } catch {
      // Backend may not be ready yet; fail silently
    }
  }, [provider])

  useEffect(() => {
    fetchDocuments()
    const id = setInterval(fetchDocuments, 30_000)
    return () => clearInterval(id)
  }, [fetchDocuments])

  function handleProviderChange(next: Provider) {
    setProvider(next)
    window.localStorage.setItem('rag-provider', next)
  }

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar documents={documents} provider={provider} onDocumentsChange={fetchDocuments} />
      <div className="flex-1 flex flex-col h-full">
        <div className="h-12 border-b border-gray-200 bg-white px-6 flex items-center justify-end">
          <div className="inline-flex rounded-lg border border-gray-300 overflow-hidden text-xs">
            <button
              onClick={() => handleProviderChange('openai')}
              className={`px-3 py-1.5 ${provider === 'openai' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'}`}
            >
              OpenAI
            </button>
            <button
              onClick={() => handleProviderChange('ollama')}
              className={`px-3 py-1.5 ${provider === 'ollama' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'}`}
            >
              Local (Ollama)
            </button>
          </div>
        </div>
        <ChatPanel hasDocuments={documents.length > 0} provider={provider} />
      </div>
    </main>
  )
}
