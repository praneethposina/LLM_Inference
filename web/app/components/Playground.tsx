'use client'

import { useState, useRef, useEffect } from 'react'

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000'
const DEFAULT_API_KEY = 'sk-dev-default-key-12345'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Playground() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [apiKey, setApiKey] = useState(DEFAULT_API_KEY)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setStreaming(true)
    setError(null)

    try {
      const response = await fetch(`${GATEWAY_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'echo-model',
          messages: [...messages, userMessage],
          stream: true,
          max_tokens: 200
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      // Handle streaming response
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantMessage: Message = { role: 'assistant', content: '' }

      setMessages(prev => [...prev, assistantMessage])

      if (reader) {
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') {
                setStreaming(false)
                continue
              }

              try {
                const chunk = JSON.parse(data)
                const content = chunk.choices?.[0]?.delta?.content
                if (content) {
                  assistantMessage.content += content
                  setMessages(prev => {
                    const newMessages = [...prev]
                    newMessages[newMessages.length - 1] = { ...assistantMessage }
                    return newMessages
                  })
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }

      setStreaming(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setStreaming(false)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 120px)'
    }}>
      <div style={{
        marginBottom: '1rem',
        padding: '1rem',
        background: '#1a1a1a',
        borderRadius: '8px',
        display: 'flex',
        gap: '1rem',
        alignItems: 'center'
      }}>
        <label style={{ fontSize: '0.9rem', color: '#999' }}>API Key:</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: '#0a0a0a',
            border: '1px solid #333',
            borderRadius: '4px',
            color: '#e0e0e0',
            fontFamily: 'monospace',
            fontSize: '0.85rem'
          }}
          placeholder="Enter API key"
        />
      </div>

      {error && (
        <div style={{
          marginBottom: '1rem',
          padding: '1rem',
          background: '#4a1a1a',
          border: '1px solid #ff4444',
          borderRadius: '8px',
          color: '#ff8888'
        }}>
          Error: {error}
        </div>
      )}

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        background: '#1a1a1a',
        borderRadius: '8px',
        marginBottom: '1rem'
      }}>
        {messages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#666',
            marginTop: '3rem'
          }}>
            <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>Playground</h2>
            <p>Start a conversation with the echo model</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: '1.5rem',
                padding: '1rem',
                background: msg.role === 'user' ? '#2a2a2a' : '#1a2a1a',
                borderRadius: '8px',
                borderLeft: `4px solid ${msg.role === 'user' ? '#60a5fa' : '#4ade80'}`
              }}
            >
              <div style={{
                fontSize: '0.85rem',
                color: '#999',
                marginBottom: '0.5rem',
                fontWeight: 600
              }}>
                {msg.role === 'user' ? 'You' : 'Assistant'}
              </div>
              <div style={{
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6',
                wordBreak: 'break-word'
              }}>
                {msg.content}
                {streaming && idx === messages.length - 1 && msg.role === 'assistant' && (
                  <span style={{ opacity: 0.5 }}>▊</span>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={isLoading}
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '8px',
            color: '#e0e0e0',
            fontSize: '1rem'
          }}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          style={{
            padding: '0.75rem 2rem',
            background: isLoading ? '#333' : '#60a5fa',
            border: 'none',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

