import { useState } from "react";
import Bubble from "./MessageBubble";
import Status from "./Status";
import FileDrop from "./FileDrop";
import useAutoScroll from "../hooks/useAutoScroll";
import { useAppContext } from "../context/AppContext";

export default function ChatPage() {
  const { chat, status, connected, send: sendWs, uploadFile } = useAppContext();
  const [input, setInput] = useState("");

  useAutoScroll([chat, status]);

  const send = () => {
    if (!input.trim() || !connected) return;
    sendWs(input);
    setInput("");
  };

  return (
    <div className="h-full flex flex-col dark:bg-gray-900">
      <main className="flex-1 overflow-y-auto p-4 space-y-3">
        {chat.map((m, i) => (
          <Bubble key={i} role={m.role}>
            {m.content}
          </Bubble>
        ))}
        <Status text={status} />
        <div id="anchor" />
      </main>
      <div className="p-3 border-t flex gap-2 dark:border-gray-700">
        <input
          className="flex-1 border rounded-xl p-2 dark:bg-gray-800 dark:border-gray-600"
          placeholder="Введите запрос…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          disabled={!connected}
          className={`px-4 rounded-xl ${
            connected ? "bg-brand text-white" : "bg-gray-300"
          }`}
        >
          ▶
        </button>
      </div>
      <FileDrop onFile={uploadFile} />
    </div>
  );
}
