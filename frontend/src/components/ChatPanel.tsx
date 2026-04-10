'use client'

import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { chat, type ChatMessage, type Provider, type Source } from '@/lib/api'

function SourceBadges({ sources }: { sources: Source[] }) {
  if (!sources.length) return null
  const unique = sources.filter((s, i, arr) => arr.findIndex((x) => x.filename === s.filename) === i)
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {unique.map((s) => (
        <span
          key={s.filename}
          className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs text-blue-700"
          title={`Relevance: ${(s.score * 100).toFixed(0)}%`}
        >
          <svg className="w-3 h-3 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z" />
          </svg>
          <span className="max-w-[160px] truncate">{s.filename}</span>
          <span className="text-blue-400">{(s.score * 100).toFixed(0)}%</span>
        </span>
      ))}
    </div>
  )
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        <p className={`text-xs font-medium mb-1 ${isUser ? 'text-right text-gray-500' : 'text-gray-500'}`}>
          {isUser ? 'You' : 'Research Assistant'}
        </p>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm'
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
          ) : (
            <div className="prose text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && msg.sources && <SourceBadges sources={msg.sources} />}
      </div>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%]">
        <p className="text-xs font-medium mb-1 text-gray-500">Research Assistant</p>
        <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel({ hasDocuments, provider }: { hasDocuments: boolean; provider: Provider }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    // Keep conversations scoped to the active provider.
    setMessages([])
    setError('')
  }, [provider])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg: ChatMessage = { role: 'user', content: text }
    const history = [...messages]
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setError('')
    setLoading(true)

    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    try {
      const res = await chat(text, history, provider)
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
      setMessages(history)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
  }

  function clearChat() {
    setMessages([])
    setError('')
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-sm font-semibold text-gray-700">Chat with your research</h2>
          {hasDocuments ? (
            <p className="text-xs text-green-600">
              Documents ready ({provider === 'openai' ? 'OpenAI' : 'Local/Ollama'}) - ask anything
            </p>
          ) : (
            <p className="text-xs text-amber-600">
              Upload PDFs for {provider === 'openai' ? 'OpenAI' : 'Local/Ollama'} in the sidebar to get started
            </p>
          )}
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <p className="text-gray-500 text-sm font-medium">Ask a question about your papers</p>
            <p className="text-gray-400 text-xs mt-1">
              Try: "What is the main contribution?" or "Summarize the methodology"
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && <ThinkingIndicator />}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-6 mb-2 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      <div className="px-6 pb-6 pt-2 bg-white border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your research papers... (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-sm
              placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:opacity-60 transition-all"
            style={{ maxHeight: 200 }}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center
              hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
