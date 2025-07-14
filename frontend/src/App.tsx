import { useEffect, useRef, useState } from "react"
import Bubble from "./components/MessageBubble"
import Status from "./components/Status"
import { WS_URL } from "./ws"

interface ChatMsg {
  role: "user" | "assistant"
  content: string
}

export default function App() {
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [status, setStatus] = useState("")
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [input, setInput] = useState("")
  const [isDark, setIsDark] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Initialize dark mode from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark)
    
    setIsDark(shouldBeDark)
    if (shouldBeDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [])

  // Toggle dark mode
  const toggleDarkMode = () => {
    const newIsDark = !isDark
    setIsDark(newIsDark)
    
    if (newIsDark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  // auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [chat, status])

  // connect / reconnect
  useEffect(() => {
    const connect = () => {
      const w = new WebSocket(WS_URL)
      
      w.onopen = () => {
        console.log("WebSocket connected")
      }
      
      w.onclose = (event) => {
        console.log(`WebSocket closed. Code: ${event.code}`)
        setTimeout(connect, 2000)
      }
      
      w.onerror = (error) => {
        console.error("WebSocket error:", error)
      }
      
      w.onmessage = e => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === "status") {
            setStatus(msg.status)
            return
          }
          if (msg.type === "chat") {
            setChat(c => [...c, { role: "assistant", content: msg.content }])
          }
        } catch {
          console.error("Failed to parse message:", e.data)
        }
      }
      
      setWs(w)
    }
    
    connect()
    return () => ws?.close()
  }, [])

  const send = () => {
    if (!input.trim()) {
      return
    }
    
    if (!ws) {
      return
    }
    
    if (ws.readyState !== 1) {
      return
    }
    
    ws.send(input.trim())
    setChat(c => [...c, { role: "user", content: input.trim() }])
    setInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  // Check if button should be disabled
  const disabled = !input.trim() || !ws || ws.readyState !== 1

  return (
    <div className="h-screen flex flex-col bg-gray-100 dark:bg-gray-900 p-4">
      
      {/* Header with theme toggle */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">IB Assistant</h1>
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-lg bg-blue-600 dark:bg-blue-700 hover:bg-blue-700 dark:hover:bg-blue-600 text-white transition-colors"
          title={isDark ? "Переключить на светлую тему" : "Переключить на тёмную тему"}
        >
          {isDark ? "☀️" : "🌙"}
        </button>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-2">
        {chat.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <Bubble role={m.role}>{m.content}</Bubble>
          </div>
        ))}
        {status && <Status status={status} />}
      </div>
      
      <div className="flex bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-xl overflow-hidden shadow-sm">
        <textarea 
          className="flex-1 p-3 resize-none border-none outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100" 
          rows={1} 
          value={input} 
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Введите запрос…"
        />
        <button 
          onClick={send} 
          disabled={disabled}
          className={`px-4 rounded-r-xl ${
            disabled 
              ? "bg-gray-300 dark:bg-gray-600 cursor-not-allowed text-gray-500 dark:text-gray-400"
              : "bg-blue-600 dark:bg-blue-700 text-white hover:bg-blue-700 dark:hover:bg-blue-600"
          }`}
        >
          ▶
        </button>
      </div>
      
      {/* Connection status */}
      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
        WS: {ws ? `${ws.readyState === 1 ? '✅' : '❌'} ${ws.readyState}` : '❌ null'} | 
        Input: "{input}" | 
        Disabled: {disabled ? 'YES' : 'NO'}
      </div>
    </div>
  )
}
