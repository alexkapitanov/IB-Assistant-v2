import { useState, useEffect, useRef } from "react"
import Header from "./components/Header"
import Bubble from "./components/MessageBubble"
import Status from "./components/Status"
import FileDrop from "./components/FileDrop"
import useAutoScroll from "./hooks/useAutoScroll"
import { WS_URL } from "./ws"

interface ChatMsg {
  role: "user" | "assistant" | "system"
  content: string
}

export default function App() {
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [status, setStatus] = useState("")
  const [input, setInput] = useState("")
  const wsRef = useRef<WebSocket>()
  const [connected, setConnected] = useState(false)

  useAutoScroll([chat, status])

  // connect WS
  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws
    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setTimeout(() => location.reload(), 2000)
    }
    ws.onmessage = e => {
      const m = JSON.parse(e.data)
      if (m.type === "status") {
        setStatus(mapStatus(m.status))
        return
      }
      setChat(c => [...c, { role: m.role ?? "assistant", content: m.content }])
      setStatus("")
    }
  }, [])

  const send = () => {
    if (!input.trim() || !connected) return
    wsRef.current?.send(JSON.stringify({ message: input }))
    setChat(c => [...c, { role: "user", content: input }])
    setInput("")
  }

  return (
    <div className="h-screen flex flex-col dark:bg-gray-900">
      <Header />
      <main className="flex-1 overflow-y-auto p-4 space-y-3">
        {chat.map((m, i) => <Bubble key={i} role={m.role}>{m.content}</Bubble>)}
        <Status text={status} />
        <div id="anchor" />
      </main>
      <div className="p-3 border-t flex gap-2 dark:border-gray-700">
        <input 
          className="flex-1 border rounded-xl p-2 dark:bg-gray-800 dark:border-gray-600"
          placeholder="Введите запрос…" 
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
        />
        <button 
          onClick={send} 
          disabled={!connected}
          className={`px-4 rounded-xl ${connected ? "bg-brand text-white" : "bg-gray-300"}`}
        >
          ▶
        </button>
      </div>
      <FileDrop onFile={f => wsRef.current?.send(`upload:${f.name}`)} />
    </div>
  )
}

function mapStatus(s?: string) {
  return s === "thinking" ? "Ассистент думает…" :
    s === "searching" ? "Ассистент ищет…" :
    s === "generating" ? "Ассистент печатает…" : ""
}
