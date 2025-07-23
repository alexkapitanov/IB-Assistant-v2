import { useState, useEffect, useRef } from "react"
import Header from "./components/Header"
import Bubble from "./components/MessageBubble"
import Status from "./components/Status"
import FileDrop from "./components/FileDrop"
import useAutoScroll from "./hooks/useAutoScroll"
import { WS_URL } from "./ws"

type ChatMsg = {
  role: "user" | "assistant" | "system";
  content: string;
};

export default function App() {
  const [chat, setChat] = useState<ChatMsg[]>([
    {
      role: "assistant",
      content:
        "Здравствуйте! Чем могу помочь по вопросам информационной безопасности?",
    },
  ]);
  const [status, setStatus] = useState("")
  const [input, setInput] = useState("")
  const wsRef = useRef<WebSocket>()
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<number>()

  useAutoScroll([chat, status])

  // connect WS
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen = () => {
        console.log("✅ WS connected")
        setConnected(true)
        // отменяем таймер переподключения при успешном соединении
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      }
      ws.onclose = () => {
        console.log("🔌 WS disconnected, attempting to reconnect...")
        setConnected(false)
        // пытаемся переподключиться через 2 секунды
        reconnectTimer.current = window.setTimeout(connect, 2000)
      }
      ws.onmessage = e => {
        try {
          const m = JSON.parse(e.data)
          if (m.type === "session") {
            console.log(`Received session ID: ${m.sessionId}`);
            // Initialize the log stream with the received session ID
            if (window.initializeLogStream) {
              window.initializeLogStream(m.sessionId);
            }
            return;
          }
          if (m.type === "status") {
            setStatus(mapStatus(m.status))
            return
          }
          setChat(c => [...c, { role: m.role ?? "assistant", content: m.content }])
          setStatus("")
        } catch (error) {
          // Если не JSON, считаем, что это просто текстовое сообщение от ассистента
          setChat(c => [...c, { role: "assistant", content: e.data }])
          setStatus("")
        }
      }
      ws.onerror = (err) => {
        console.error("WS error:", err)
        ws.close() // это вызовет onclose и запустит логику переподключения
      }
    }

    connect()

    // очистка при размонтировании компонента
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])

  const send = () => {
    if (!input.trim() || !connected) return
    wsRef.current?.send(input)
    setChat(c => [...c, { role: "user", content: input }])
    setInput("")
  }

  return (
    <div className="h-screen flex flex-col dark:bg-gray-900">
      <Header connected={connected} />
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
