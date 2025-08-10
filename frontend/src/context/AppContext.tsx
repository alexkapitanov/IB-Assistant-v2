import React, { createContext, useState, useEffect, useRef, useContext, ReactNode } from 'react';
import { WS_URL } from '../ws';

// Определение типов
export type ChatMsg = {
  role: "user" | "assistant" | "system" | "file";
  content: string;
  name?: string;
};

interface AppContextType {
  chat: ChatMsg[];
  status: string;
  connected: boolean;
  send: (message: string) => void;
  uploadFile: (file: File) => void;
}

// Создание контекста с начальным значением undefined
const AppContext = createContext<AppContextType | undefined>(undefined);

// Функция для маппинга статусов (если она у вас есть)
const mapStatus = (status: string) => {
    // Примерная реализация, адаптируйте под ваши нужды
    const statusMap: { [key: string]: string } = {
        'thinking': 'Анализирую запрос...',
        'searching': 'Ищу информацию...',
        'generating': 'Генерирую ответ...',
    };
    return statusMap[status] || status;
}


// Компонент-провайдер
export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
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
          const m = JSON.parse(e.data);
          if (m.type === "session") {
            console.log(`Received session ID: ${m.sessionId}`);
            if (window.initializeLogStream) {
              window.initializeLogStream(m.sessionId);
            }
            return;
          }
          if (m.type === "status") {
            setStatus(mapStatus(m.status));
            return;
          }
          // Явно поддерживаем чатовые сообщения нового протокола
          if (m.type === "chat") {
            setChat((c) => [...c, { role: m.role ?? "assistant", content: m.content }]);
            setStatus("");
            return;
          }
          if (m.type === "error") {
            const id = m.id ? ` (ID ${m.id})` : "";
            const text = m.content || m.msg || "Неизвестная ошибка";
            setChat((c) => [...c, { role: "system", content: `⚠️ ${text}${id}` }]);
            setStatus("");
            return;
          }
          if (m.type === "file") {
            setChat((c) => [...c, { role: "file", content: m.url, name: m.name }]);
            setStatus("");
            return;
          }
          setChat((c) => [...c, { role: m.role ?? "assistant", content: m.content }]);
          setStatus("");
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

  const send = (message: string) => {
    if (!message.trim() || !connected) return;
  // Бэкенд ожидает JSON {"message": string}
  wsRef.current?.send(JSON.stringify({ message }));
    setChat((c) => [...c, { role: "user", content: message }]);
  };

  const uploadFile = (file: File) => {
    if (!connected) return;
    // Предполагается, что сервер ожидает специальное сообщение для начала загрузки файла
    const message = { message: `upload:${file.name}` };
    wsRef.current?.send(JSON.stringify(message));
    // Здесь можно добавить логику для отображения статуса загрузки файла в UI
    console.log(`Initiating upload for: ${file.name}`);
  };

  const value = {
    chat,
    status,
    connected,
    send,
    uploadFile,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Хук для удобного использования контекста
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
