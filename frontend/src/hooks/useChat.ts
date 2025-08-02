import { useState, useEffect, useRef } from "react";
import { WS_URL } from "../ws";

// Типы сообщений и статусов
export type ChatMsg = {
  role: "user" | "assistant" | "system";
  content: string;
};

type WsMessage = {
  type: "session" | "status" | "message";
  sessionId?: string;
  status?: string;   // stage
  detail?: string;   // optional detail
  role?: "user" | "assistant";
  content?: string;
};

// Кастомный хук для управления логикой чата
export function useChat() {
  const [chat, setChat] = useState<ChatMsg[]>([
    {
      role: "assistant",
      content: "Здравствуйте! Чем могу помочь по вопросам информационной безопасности?",
    },
  ]);
  const [status, setStatus] = useState("");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket>();
  const reconnectTimer = useRef<number>();

  // Функция для маппинга статусов
  const mapStatus = (s?: string) => {
    return s === "thinking" ? "Ассистент думает…" :
           s === "searching" ? "Ассистент ищет…" :
           s === "generating" ? "Ассистент печатает…" : "";
  };

  // Управление WebSocket соединением
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("✅ WS connected");
        setConnected(true);
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      };

      ws.onclose = () => {
        console.log("🔌 WS disconnected, attempting to reconnect...");
        setConnected(false);
        reconnectTimer.current = window.setTimeout(connect, 2000);
      };

      ws.onmessage = (e) => {
        try {
          const m: WsMessage = JSON.parse(e.data);
          switch (m.type) {
            case "session":
              console.log(`Received session ID: ${m.sessionId}`);
              if (window.initializeLogStream && m.sessionId) {
                window.initializeLogStream(m.sessionId);
              }
              break;
          case "status":
            // показываем stage + detail, auto-hide on "done"
            if (m.status) {
              const text = mapStatus(m.status) + (m.detail ? `: ${m.detail}` : "");
              setStatus(text);
              if (m.status === "done") {
                setTimeout(() => setStatus(""), 2000);
              }
            }
            return;
            default:
              if (m.content) {
                setChat((c) => [...c, { role: m.role ?? "assistant", content: m.content as string }]);
              }
              setStatus("");
          }
        } catch (error) {
          setChat((c) => [...c, { role: "assistant", content: e.data }]);
          setStatus("");
        }
      };

      ws.onerror = (err) => {
        console.error("WS error:", err);
        ws.close();
      };
    };

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  // Функция отправки сообщения
  const sendMessage = (message: string) => {
    if (!message.trim() || !connected) return;
    wsRef.current?.send(message);
    setChat((c) => [...c, { role: "user", content: message }]);
  };
  
  // Функция отправки файла
  const sendFile = (file: File) => {
    if (!connected) return;
    // В будущем здесь может быть более сложная логика, 
    // например, загрузка на сервер и отправка ссылки
    wsRef.current?.send(`upload:${file.name}`);
    setChat((c) => [...c, { role: "user", content: `Файл для загрузки: ${file.name}` }]);
  }

  return { chat, status, connected, sendMessage, sendFile };
}
