import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface LogEntry {
  id: number;
  timestamp: string;
  message: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logIdCounter = useRef(0);
  const navigate = useNavigate();

  // Автоскролл к последнему логу
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // Функция для подключения к потоку логов
  const connectToLogs = (newSessionId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setSessionId(newSessionId);
    setLogs([]);
    setError(null);
    setConnected(false);

    const backendHost = `${window.location.hostname}:8000`;
    const logUrl = `http://${backendHost}/logs/${newSessionId}`;
    
    const eventSource = new EventSource(logUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
      addLogEntry('INFO', `Подключение к потоку логов для сессии ${newSessionId} установлено`);
    };

    eventSource.onmessage = (event) => {
      const logMessage = event.data;
      
      // Простое определение уровня лога по содержимому
      let level: LogEntry['level'] = 'INFO';
      if (logMessage.includes('ERROR')) {
        level = 'ERROR';
      } else if (logMessage.includes('WARNING')) {
        level = 'WARNING';
      } else if (logMessage.includes('DEBUG')) {
        level = 'DEBUG';
      }

      addLogEntry(level, logMessage);
    };

    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      setError('Ошибка соединения с потоком логов. Переподключение...');
      setConnected(false);
      // EventSource автоматически пытается переподключиться
    };
  };

  const addLogEntry = (level: LogEntry['level'], message: string) => {
    const newLog: LogEntry = {
      id: ++logIdCounter.current,
      timestamp: new Date().toLocaleTimeString(),
      level,
      message
    };

    setLogs(prevLogs => [...prevLogs, newLog]);
  };

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Глобальная функция для инициализации из чата
  useEffect(() => {
    (window as any).initializeLogStream = connectToLogs;
    
    return () => {
      delete (window as any).initializeLogStream;
    };
  }, []);

  const handleSessionIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    const inputSessionId = formData.get('sessionId') as string;
    
    if (inputSessionId?.trim()) {
      connectToLogs(inputSessionId.trim());
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const getLogLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'ERROR': return 'text-red-400';
      case 'WARNING': return 'text-yellow-400';
      case 'DEBUG': return 'text-gray-500';
      default: return 'text-gray-300';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-gray-200">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-white">Логи сессии</h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm">
                {connected ? 'Подключено' : 'Отключено'}
              </span>
            </div>
            <button
              onClick={clearLogs}
              className="px-3 py-1 text-sm bg-gray-700 text-gray-300 rounded-md hover:bg-gray-600 transition-colors"
            >
              🗑️ Очистить
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              💬 Чат
            </button>
          </div>
        </div>

        {/* Session ID input */}
        <form onSubmit={handleSessionIdSubmit} className="mt-3 flex gap-2">
          <input
            name="sessionId"
            type="text"
            placeholder="Введите ID сессии для просмотра логов"
            className="flex-1 px-3 py-1 text-sm bg-gray-700 text-white border border-gray-600 rounded-md focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            className="px-4 py-1 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            Подключиться
          </button>
        </form>

        {sessionId && (
          <div className="mt-2 text-sm text-gray-400">
            Текущая сессия: <code className="bg-gray-700 px-2 py-1 rounded">{sessionId}</code>
          </div>
        )}

        {error && (
          <div className="mt-2 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {/* Logs area */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs bg-gray-900">
        {logs.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            {sessionId ? 'Ожидание логов сессии...' : 'Введите ID сессии для просмотра логов'}
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-2">
                <span className="text-gray-500 min-w-20">[{log.timestamp}]</span>
                <span className={`min-w-16 ${getLogLevelColor(log.level)}`}>
                  {log.level}
                </span>
                <span className="text-gray-300 break-all">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-800 border-t border-gray-700 p-2 text-xs text-gray-500 text-center">
        Логи обновляются в реальном времени через Server-Sent Events
      </div>
    </div>
  );
}
