import { useEffect, useRef, useState } from "react"
import Bubble from "./components/MessageBubble"
import Status from "./components/Status"
import { WS_URL } from "./ws"

interface ChatMsg {
  role: "user" | "assistant"
  content: string
}

export default function App() {
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [status, setStatus] = useState<string>("")
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  // auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [chat, status])

  // connect / reconnect
  useEffect(() => {
    const connect = () => {
      updateDebug(`Attempting to connect to: ${WS_URL}`)
      const w = new WebSocket(WS_URL)
      
      w.onopen = () => {
        updateDebug("✅ WebSocket connected successfully")
        console.log("ReadyState:", w.readyState)
      }
      
      w.onclose = (event) => {
        updateDebug(`❌ WebSocket closed. Code: ${event.code}, Reason: "${event.reason}"`)
        setTimeout(connect, 2000)
      }
      
      w.onerror = (error) => {
        updateDebug("🔥 WebSocket error occurred")
        console.error("WebSocket error:", error)
      }
      
      w.onmessage = e => {
        updateDebug(`📨 Received message: ${e.data}`)
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === "status") {
            setStatus(msg.status)
            return
          }
          setChat(c => [...c, { role: msg.role ?? "assistant", content: msg.answer || msg.content || e.data }])
          setStatus("")
        } catch (err) {
          console.error("Failed to parse message:", err, e.data)
        }
      }
      setWs(w)
    }
    connect()
  }, [])

  const send = () => {
    updateDebug("🚀 Send function called!")
    
    const debugData = { 
      input: input.trim(), 
      inputLength: input.length,
      inputTrimmed: input.trim(),
      wsExists: !!ws, 
      readyState: ws?.readyState,
      wsReadyStateText: ws?.readyState === 0 ? "CONNECTING" : 
                       ws?.readyState === 1 ? "OPEN" : 
                       ws?.readyState === 2 ? "CLOSING" : 
                       ws?.readyState === 3 ? "CLOSED" : "UNKNOWN"
    }
    
    console.log("🚀 Send attempt with data:", debugData)
    updateDebug(`Send data: ${JSON.stringify(debugData)}`)
    
    if (!input.trim()) {
      updateDebug("❌ Message is empty after trim")
      return
    }
    
    if (!ws) {
      updateDebug("❌ WebSocket is null")
      return
    }
    
    if (ws.readyState !== 1) {
      updateDebug(`❌ WebSocket not open. ReadyState: ${ws.readyState}`)
      return
    }
    
    updateDebug(`📤 Sending message: "${input}"`)
    ws.send(input)
    setChat(c => [...c, { role: "user", content: input }])
    setInput("")
    updateDebug("✅ Message sent and input cleared")
  }

  // Button click handler with debug
  const handleButtonClick = () => {
    console.log("🔘 Button clicked!")
    updateDebug("🔘 Button clicked!")
    send()
  }

  // Key handler with debug
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      console.log("⌨️ Enter key pressed!")
      updateDebug("⌨️ Enter key pressed!")
      send()
    }
  }

  // Check if button should be disabled
  const disabled = !input.trim() || !ws || ws.readyState !== 1

  return (
    <div className="h-screen flex flex-col bg-gray-100 p-4">
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-2">
        {chat.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <Bubble role={m.role}>{m.content}</Bubble>
          </div>
        ))}
        <Status text={status} />
      </div>
      
      <div className="mt-2 flex">
        <input
          className="flex-1 border rounded-l-xl p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={input}
          onChange={e => {
            setInput(e.target.value)
            updateDebug(`Input changed: "${e.target.value}"`)
          }}
          onKeyDown={handleKeyDown}
          placeholder="Введите запрос…"
        />
        <button 
          onClick={send} 
          disabled={disabled}
          className={`px-4 rounded-r-xl ${
            disabled 
              ? "bg-gray-300 cursor-not-allowed"
              : "bg-blue-600 text-white"
          }`}
        >
          ▶
        </button>
      </div>
      
      {/* Connection status */}
      <div className="mt-1 text-xs text-gray-500">
        WS: {ws ? `${ws.readyState === 1 ? '✅' : '❌'} ${ws.readyState}` : '❌ null'} | 
        Input: "{input}" | 
        Disabled: {disabled ? 'YES' : 'NO'}
      </div>
    </div>
  )
}
