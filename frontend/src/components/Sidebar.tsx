'use client'

import { useRef, useState } from 'react'
import { deleteDocument, uploadDocument, type Document, type Provider } from '@/lib/api'

interface SidebarProps {
  documents: Document[]
  provider: Provider
  onDocumentsChange: () => void
}

export default function Sidebar({ documents, provider, onDocumentsChange }: SidebarProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploadError('')
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file, provider)
      }
      onDocumentsChange()
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDelete(docId: string) {
    setDeletingId(docId)
    try {
      await deleteDocument(docId, provider)
      onDocumentsChange()
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <aside className="w-72 flex-shrink-0 bg-gray-900 text-gray-100 flex flex-col h-full">
      <div className="px-5 py-5 border-b border-gray-700">
        <h1 className="text-lg font-semibold tracking-tight">Research RAG</h1>
        <p className="text-xs text-gray-400 mt-0.5">Academic PDF assistant</p>
        <p className="text-[11px] text-gray-500 mt-1">Provider: {provider === 'openai' ? 'OpenAI' : 'Local (Ollama)'}</p>
      </div>

      <div className="px-4 py-4 border-b border-gray-700">
        <div
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors
            ${dragOver ? 'border-blue-400 bg-blue-900/20' : 'border-gray-600 hover:border-gray-500'}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            handleFiles(e.dataTransfer.files)
          }}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-gray-400">Ingesting PDF...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1">
              <svg className="w-7 h-7 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <span className="text-xs text-gray-400">Drop PDFs or click to upload</span>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploadError && <p className="mt-2 text-xs text-red-400">{uploadError}</p>}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Documents ({documents.length})</p>
        {documents.length === 0 ? (
          <p className="text-xs text-gray-600 italic">No PDFs ingested yet</p>
        ) : (
          <ul className="space-y-1">
            {documents.map((doc) => (
              <li
                key={doc.doc_id}
                className="flex items-center gap-2 group rounded-md px-2 py-1.5 hover:bg-gray-800 transition-colors"
              >
                <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
                </svg>
                <span className="text-xs text-gray-300 flex-1 truncate" title={doc.filename}>
                  {doc.filename}
                </span>
                <button
                  onClick={() => handleDelete(doc.doc_id)}
                  disabled={deletingId === doc.doc_id}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all"
                  title="Remove document"
                >
                  {deletingId === doc.doc_id ? (
                    <div className="w-3.5 h-3.5 border border-gray-500 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="px-4 py-3 border-t border-gray-700">
        <p className="text-xs text-gray-600">WillardServices</p>
      </div>
    </aside>
  )
}
