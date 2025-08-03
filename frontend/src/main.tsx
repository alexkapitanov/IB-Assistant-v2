import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import { MainLayout } from "./components/MainLayout";
import ChatPage from "./components/ChatPage";
import Grafana from "./pages/Grafana";
import LogsPage from "./components/LogsPage";
import "./index.css";

console.log('main.tsx loaded');

// Создание маршрутов
const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <ChatPage />,
      },
      {
        path: "grafana",
        element: <Grafana />,
      },
      {
        path: "logs",
        element: <LogsPage />,
      },
    ],
  },
]);

function renderApp() {
  const rootContainer = document.getElementById("root");
  console.log('Root element:', rootContainer);
  if (rootContainer) {
    ReactDOM.createRoot(rootContainer).render(
      <AppProvider>
        <RouterProvider router={router} />
      </AppProvider>
    );
    console.log('React rendered');
  } else {
    console.error('Root element not found!');
  }
}

window.addEventListener('error', (e) => {
  console.error('Runtime error:', e.error);
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", renderApp);
} else {
  renderApp();
}

// --- Tab and Log Streaming Logic ---

const tabChat = document.getElementById("tab-chat");
const tabLogs = document.getElementById("tab-logs");
const contentChat = document.getElementById("content-chat");
const contentLogs = document.getElementById("content-logs");
const logsContainer = document.getElementById("logs-container");

let eventSource: EventSource | null = null;
let sessionId: string | null = null;

// Function to initialize the log stream
window.initializeLogStream = (newSessionId: string) => {
  if (sessionId === newSessionId && eventSource) {
    return; // Already connected for this session
  }

  sessionId = newSessionId;

  // Close any existing connection
  if (eventSource) {
    eventSource.close();
  }

  if (!logsContainer) return;
  logsContainer.innerHTML = `<p class="text-green-400">Подключение к потоку логов для сессии ${sessionId}...</p>`;

  const wsProtocol = window.location.protocol === "https:" ? "https" : "http";
  // В Docker контейнере бэкенд может быть на другом порту, если не используется reverse proxy
  // Для локальной разработки обычно тот же хост, но может быть другой порт (например, 8000)
  // Эта конструкция пытается угадать порт, но может потребовать ручной настройки
  const backendHost = `${window.location.hostname}:8000`;
  const logUrl = `${wsProtocol}://${backendHost}/logs/${sessionId}`;
  
  eventSource = new EventSource(logUrl);

  eventSource.onopen = () => {
    if (logsContainer) {
      logsContainer.innerHTML += `<p class="text-green-400">Соединение для логов установлено.</p>`;
    }
  };

  eventSource.onmessage = (event) => {
    if (logsContainer) {
      // Clear initial message if it's still there
      const initialMsg = logsContainer.querySelector("p");
      if (initialMsg && initialMsg.textContent?.startsWith("Ожидание")) {
        logsContainer.innerHTML = "";
      }
      const logEntry = document.createElement("div");
      logEntry.textContent = event.data;
      // Simple coloring based on log level
      if (event.data.includes("ERROR")) {
        logEntry.className = "text-red-400";
      } else if (event.data.includes("WARNING")) {
        logEntry.className = "text-yellow-400";
      } else {
        logEntry.className = "text-gray-300";
      }
      logsContainer.appendChild(logEntry);
      logsContainer.scrollTop = logsContainer.scrollHeight; // Auto-scroll
    }
  };

  eventSource.onerror = (err) => {
    if (logsContainer) {
      logsContainer.innerHTML += `<p class="text-red-500">Ошибка соединения с потоком логов. Переподключение...</p>`;
    }
    console.error("EventSource failed:", err);
    // EventSource will automatically try to reconnect.
  };
};

// Tab switching logic
tabChat?.addEventListener("click", () => {
  contentChat?.classList.remove("hidden");
  contentLogs?.classList.add("hidden");
  tabChat.classList.add("bg-white");
  tabChat.classList.remove("text-gray-500");
  tabLogs?.classList.add("text-gray-500");
  tabLogs?.classList.remove("bg-white");
});

tabLogs?.addEventListener("click", () => {
  contentChat?.classList.add("hidden");
  contentLogs?.classList.remove("hidden");
  tabLogs.classList.add("bg-white");
  tabLogs.classList.remove("text-gray-500");
  tabChat?.classList.add("text-gray-500");
  tabChat?.classList.remove("bg-white");
});
