const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export type Provider = 'openai' | 'ollama'

export interface Document {
  doc_id: string
  filename: string
}

export interface Source {
  filename: string
  score: number
  chunk_index: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export interface ChatResponse {
  answer: string
  sources: Source[]
}

export async function uploadDocument(
  file: File,
  provider: Provider
): Promise<{ status: string; filename: string; chunks: number; provider: Provider }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('provider', provider)
  const res = await fetch(`${API_URL}/ingest`, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function getDocuments(provider: Provider): Promise<Document[]> {
  const res = await fetch(`${API_URL}/documents?provider=${encodeURIComponent(provider)}`)
  if (!res.ok) throw new Error('Failed to fetch documents')
  const data = await res.json()
  return data.documents as Document[]
}

export async function deleteDocument(docId: string, provider: Provider): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${docId}?provider=${encodeURIComponent(provider)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete document')
}

export async function chat(message: string, history: ChatMessage[], provider: Provider): Promise<ChatResponse> {
  const conversation_history = history.map((m) => ({ role: m.role, content: m.content }))
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_history, provider }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }))
    throw new Error(err.detail || 'Chat failed')
  }
  return res.json()
}
