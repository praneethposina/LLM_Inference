'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:8000'
const DEFAULT_API_KEY = 'sk-dev-default-key-12345'

interface ApiKey {
  key_id: string
  prefix: string
  created_at: string
  rate_limit: number
  active: boolean
}

interface UsageStats {
  total_requests: number
  total_tokens: number
  avg_latency_ms: number
}

export default function Console() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyRateLimit, setNewKeyRateLimit] = useState(30)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadApiKeys()
    loadUsageStats()
    
    // Refresh stats every 5 seconds
    const interval = setInterval(() => {
      loadUsageStats()
    }, 5000)
    
    return () => clearInterval(interval)
  }, [])

  const loadApiKeys = async () => {
    try {
      const response = await fetch(`${GATEWAY_URL}/v1/keys`)
      if (!response.ok) {
        throw new Error('Failed to load API keys')
      }
      const data = await response.json()
      setApiKeys(data.data || [])
    } catch (err) {
      console.error('Failed to load API keys:', err)
      // Fallback to default key on error
      setApiKeys([{
        key_id: 'default',
        prefix: 'sk-dev-default-key...',
        created_at: new Date().toISOString(),
        rate_limit: 30,
        active: true
      }])
    }
  }

  const loadUsageStats = async () => {
    try {
      const response = await fetch(`${GATEWAY_URL}/v1/usage`)
      if (!response.ok) {
        throw new Error('Failed to load usage stats')
      }
      const stats = await response.json()
      setUsageStats(stats)
    } catch (err) {
      console.error('Failed to load usage stats:', err)
      // Fallback to zero stats
      setUsageStats({
        total_requests: 0,
        total_tokens: 0,
        avg_latency_ms: 0
      })
    }
  }

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return

    setLoading(true)
    try {
      const response = await fetch(`${GATEWAY_URL}/v1/keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          key_id: newKeyName.trim(),
          rate_limit: newKeyRateLimit
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create key')
      }
      
      const data = await response.json()
      setCreatedKey(data.api_key)
      setNewKeyName('')
      
      // Reload keys
      await loadApiKeys()
    } catch (err) {
      console.error('Failed to create key:', err)
      alert(err instanceof Error ? err.message : 'Failed to create key')
    } finally {
      setLoading(false)
    }
  }

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm(`Are you sure you want to revoke key "${keyId}"?`)) {
      return
    }

    try {
      const response = await fetch(`${GATEWAY_URL}/v1/keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${DEFAULT_API_KEY}`
        }
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to revoke key')
      }
      
      // Reload keys
      await loadApiKeys()
    } catch (err) {
      console.error('Failed to revoke key:', err)
      alert(err instanceof Error ? err.message : 'Failed to revoke key')
    }
  }

  return (
    <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        borderBottom: '1px solid #333',
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>LLM Inference Service</h1>
        <nav style={{ display: 'flex', gap: '2rem' }}>
          <Link href="/" style={{ color: '#60a5fa', textDecoration: 'none' }}>
            Playground
          </Link>
          <Link href="/console" style={{ color: '#60a5fa', textDecoration: 'none' }}>
            Console
          </Link>
        </nav>
      </header>

      <div style={{ flex: 1, padding: '2rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <h2 style={{ fontSize: '2rem', marginBottom: '2rem' }}>Console</h2>

        {/* Usage Stats */}
        <section style={{
          marginBottom: '3rem',
          padding: '1.5rem',
          background: '#1a1a1a',
          borderRadius: '8px'
        }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Usage Statistics</h3>
          {usageStats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.85rem', color: '#999', marginBottom: '0.5rem' }}>Total Requests</div>
                <div style={{ fontSize: '2rem', fontWeight: 600 }}>{usageStats.total_requests}</div>
              </div>
              <div style={{ padding: '1rem', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.85rem', color: '#999', marginBottom: '0.5rem' }}>Total Tokens</div>
                <div style={{ fontSize: '2rem', fontWeight: 600 }}>{usageStats.total_tokens.toLocaleString()}</div>
              </div>
              <div style={{ padding: '1rem', background: '#0a0a0a', borderRadius: '4px' }}>
                <div style={{ fontSize: '0.85rem', color: '#999', marginBottom: '0.5rem' }}>Avg Latency</div>
                <div style={{ fontSize: '2rem', fontWeight: 600 }}>{usageStats.avg_latency_ms}ms</div>
              </div>
            </div>
          ) : (
            <div style={{ color: '#666' }}>Loading statistics...</div>
          )}
        </section>

        {/* API Keys */}
        <section style={{
          marginBottom: '3rem',
          padding: '1.5rem',
          background: '#1a1a1a',
          borderRadius: '8px'
        }}>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>API Keys</h3>

          {/* Create New Key */}
          <div style={{
            marginBottom: '2rem',
            padding: '1rem',
            background: '#0a0a0a',
            borderRadius: '4px',
            display: 'flex',
            gap: '1rem',
            alignItems: 'flex-end'
          }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#999', marginBottom: '0.5rem' }}>
                Key Name
              </label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="my-api-key"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  background: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: '4px',
                  color: '#e0e0e0'
                }}
              />
            </div>
            <div style={{ width: '150px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#999', marginBottom: '0.5rem' }}>
                Rate Limit (req/min)
              </label>
              <input
                type="number"
                value={newKeyRateLimit}
                onChange={(e) => setNewKeyRateLimit(parseInt(e.target.value) || 30)}
                min="1"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  background: '#1a1a1a',
                  border: '1px solid #333',
                  borderRadius: '4px',
                  color: '#e0e0e0'
                }}
              />
            </div>
            <button
              onClick={handleCreateKey}
              disabled={loading || !newKeyName.trim()}
              style={{
                padding: '0.5rem 1.5rem',
                background: loading ? '#333' : '#4ade80',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? 'Creating...' : 'Create Key'}
            </button>
          </div>

          {createdKey && (
            <div style={{
              marginBottom: '1rem',
              padding: '1rem',
              background: '#1a2a1a',
              border: '1px solid #4ade80',
              borderRadius: '4px',
              color: '#4ade80'
            }}>
              <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>New API Key Created:</div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.9rem', wordBreak: 'break-all' }}>
                {createdKey}
              </div>
              <div style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: '#999' }}>
                Save this key - it won't be shown again!
              </div>
            </div>
          )}

          {/* Key List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {apiKeys.map((key, idx) => (
              <div
                key={idx}
                style={{
                  padding: '1rem',
                  background: '#0a0a0a',
                  borderRadius: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{key.key_id}</div>
                  <div style={{ fontSize: '0.85rem', color: '#666', fontFamily: 'monospace' }}>
                    {key.prefix}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.25rem' }}>
                    Created: {new Date(key.created_at).toLocaleDateString()} • 
                    Rate Limit: {key.rate_limit}/min • 
                    Status: {key.active ? 'Active' : 'Inactive'}
                  </div>
                </div>
                <button
                  onClick={() => handleRevokeKey(key.key_id)}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#4a1a1a',
                    border: '1px solid #ff4444',
                    borderRadius: '4px',
                    color: '#ff8888',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}

