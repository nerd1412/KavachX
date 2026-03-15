import { useState, useRef, useEffect } from 'react'
import { Send, Shield, Zap, Info, User, Bot, RefreshCw, ChevronDown, Sparkles, MessageSquare } from 'lucide-react'
import { governanceAPI, modelsAPI } from '../utils/api'
import { useAuth } from '../context/AuthContext'

export default function GovernedChat() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `Hello ${user?.name || 'there'}. I am your Governed AI assistant. Everything you type here is monitored for security and compliance. How can I help you today?` }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState('chatgpt')
  const [models, setModels] = useState([
    { id: 'chatgpt', name: 'ChatGPT (GPT-4o)', provider: 'OpenAI' },
    { id: 'claude', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
    { id: 'gemini', name: 'Gemini 1.5 Pro', provider: 'Google' },
    { id: 'deepseek', name: 'DeepSeek-V3', provider: 'DeepSeek' }
  ])
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch real models if available and merge them
  useEffect(() => {
    modelsAPI.list().then(res => {
        if (res.data?.length > 0) {
            // Merge unique models while keeping hardcoded ones
            setModels(prev => {
                const combined = [...prev];
                res.data.forEach(m => {
                    const id = m.id || m.model_name;
                    if (!combined.find(x => x.id === id)) {
                        combined.push({ id, name: m.name || m.model_name, provider: m.provider || 'External' });
                    }
                });
                return combined;
            });
        }
    }).catch(() => { /* Silent fallback to hardcoded */ })
  }, [])

  const handleSend = async (e) => {
    e?.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setLoading(true)

    try {
      // 1. Governance Evaluation (Using simulate to ensure auto-registration of new AI platforms)
      const selectedModelData = models.find(m => m.id === selectedModel)
      const res = await governanceAPI.simulate({
        model_id: selectedModel,
        input_data: { 
            prompt: currentInput,
            platform: selectedModelData?.name || selectedModel,
            source: "Governed Chat Portal"
        },
        prediction: { text: "Governed Analysis in progress..." },
        confidence: 0.99,
        context: { 
            user_id: user?.id,
            user_role: user?.role,
            is_mobile: window.innerWidth < 768
        },
        session_id: "web-chat-" + (user?.id || 'demo')
      })

      const gov = res.data

      if (gov.enforcement_decision === 'BLOCK') {
        setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: `🚨 **Access Denied**: My security filters blocked this request.\n\n**Reason**: ${gov.explanation?.reason || 'Policy Violation Detected.'}`,
            isBlocked: true 
        }])
      } else {
        // 2. Mock AI Response (Industry standard behavior)
        // In a real production environment, this would call the actual LLM API here.
        setTimeout(() => {
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: `I've analyzed your request. This prompt has been cleared by KavachX (Risk Score: ${(gov.risk_score * 100).toFixed(1)}%).\n\nHow else can I assist with your governed workflows?` 
            }])
        }, 800)
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "⚠️ **System Error**: Could not reach the governance engine. Check your connection.", isError: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-page" style={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column', maxWidth: '900px', margin: '0 auto' }}>
      {/* Header / Model Selector */}
      <div style={{ padding: '0 0 20px 0', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
            <h1 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text)' }}>Governed AI Chat</h1>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Real-time monitoring enabled • Secure Session</p>
        </div>
        <div style={{ position: 'relative' }}>
            <select 
                value={selectedModel} 
                onChange={(e) => setSelectedModel(e.target.value)}
                style={{ 
                    appearance: 'none', padding: '8px 32px 8px 12px', borderRadius: '8px', 
                    background: 'var(--bg-card)', border: '1px solid var(--border)',
                    fontSize: '12px', fontWeight: 600, color: 'var(--text)', cursor: 'pointer'
                }}
            >
                {models.map(m => (
                    <option key={m.id} value={m.id}>{m.name || m.model_name}</option>
                ))}
            </select>
            <ChevronDown size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
        </div>
      </div>

      {/* Messages Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 0', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', gap: '16px', maxWidth: '100%', flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{ 
                width: '34px', height: '34px', borderRadius: '10px', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: m.role === 'user' ? 'var(--accent)' : 'var(--bg-elevated)',
                color: m.role === 'user' ? '#fff' : 'var(--accent)',
                border: m.role === 'user' ? 'none' : '1px solid var(--border)'
            }}>
              {m.role === 'user' ? <User size={18} /> : <Shield size={18} />}
            </div>
            <div style={{ 
                padding: '12px 16px', borderRadius: '14px', fontSize: '14px', lineHeight: 1.6,
                background: m.role === 'user' ? 'var(--accent)' : m.isBlocked ? 'var(--red-light)' : 'var(--bg-card)',
                color: m.role === 'user' ? '#fff' : 'var(--text)',
                border: m.role === 'user' ? 'none' : `1px solid ${m.isBlocked ? 'var(--red)' : 'var(--border)'}`,
                boxShadow: 'var(--shadow-sm)', maxWidth: '80%', whiteSpace: 'pre-wrap'
            }}>
              {m.content}
              {m.isBlocked && <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: 'var(--red)' }}><Info size={12} /> Reported to Compliance Dashboard</div>}
            </div>
          </div>
        ))}
        {loading && (
            <div style={{ display: 'flex', gap: '16px' }}>
                 <div style={{ width: '34px', height: '34px', borderRadius: '10px', background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <RefreshCw size={18} className="spin" color="var(--accent)" />
                 </div>
                 <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic' }}>Kavach AI is evaluating your prompt...</div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Footer / Input */}
      <div style={{ padding: '20px 0', borderTop: '1px solid var(--border)' }}>
        <form onSubmit={handleSend} style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ flex: 1, position: 'relative' }}>
                <textarea 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend(e)}
                    placeholder="Message Governed AI..."
                    style={{ 
                        width: '100%', padding: '14px 44px 14px 16px', borderRadius: '12px',
                        background: 'var(--bg-card)', color: 'var(--text)', border: '1px solid var(--border)',
                        fontSize: '14px', resize: 'none', height: '52px', outline: 'none', transition: 'border-color 0.2s'
                    }}
                />
                <button 
                    type="submit" 
                    disabled={loading || !input.trim()}
                    style={{ 
                        position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                        background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '8px',
                        width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', opacity: (loading || !input.trim()) ? 0.4 : 1
                    }}
                >
                    <Send size={16} />
                </button>
            </div>
        </form>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '10px', color: 'var(--text-muted)' }}>
                <Sparkles size={12} /> Powered by KavachX Engine
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '10px', color: 'var(--text-muted)' }}>
                <MessageSquare size={12} /> Enterprise Privacy Mode
            </div>
        </div>
      </div>
    </div>
  )
}
