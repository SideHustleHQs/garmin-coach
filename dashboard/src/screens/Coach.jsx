import { useState, useEffect, useRef } from 'react'
import { sendChatMessage, getChatHistory } from '../api'

export default function Coach({ athleteId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!athleteId) return
    getChatHistory(athleteId)
      .then(hist => setMessages(hist.map(h => ({ role: h.role, content: h.content }))))
      .catch(() => {})
  }, [athleteId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)
    try {
      const data = await sendChatMessage(athleteId, msg)
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Er ging iets mis. Probeer opnieuw.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', padding: '0 16px' }}>
      <div style={{ padding: '12px 0 8px' }}>
        <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.06em', margin: 0 }}>
          AI Coach · Claude Sonnet
        </p>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: 12 }}>
        {messages.length === 0 && !loading && (
          <p style={{ color: 'var(--muted)', fontSize: 13, margin: '24px 0', textAlign: 'center' }}>
            Stel een vraag over je training.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
            background: m.role === 'user' ? 'var(--blue)' : 'var(--card)',
            color: m.role === 'user' ? '#fff' : 'var(--ink)',
            borderRadius: m.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
            padding: '9px 13px', fontSize: 14, lineHeight: 1.4,
          }}>
            {m.content}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start', color: 'var(--muted)', fontSize: 13 }}>
            Coach denkt na…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ display: 'flex', gap: 8, paddingBottom: 16 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Vraag de coach iets…"
          style={{
            flex: 1, background: 'var(--card)', border: '1px solid var(--line)',
            borderRadius: 22, padding: '10px 16px', color: 'var(--ink)',
            fontSize: 14, outline: 'none',
          }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            background: loading ? 'var(--line)' : 'var(--blue)', color: '#fff',
            border: 'none', borderRadius: '50%', width: 42, height: 42,
            fontSize: 18, cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          ↑
        </button>
      </div>
    </div>
  )
}
