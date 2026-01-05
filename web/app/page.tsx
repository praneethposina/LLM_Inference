'use client'

import { useState } from 'react'
import Link from 'next/link'
import Playground from './components/Playground'

export default function Home() {
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
      
      <div style={{ flex: 1, padding: '2rem' }}>
        <Playground />
      </div>
    </main>
  )
}

