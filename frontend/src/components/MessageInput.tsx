import { useState } from "react";

type Props = {
  onSend: (message: string) => void;
  connected: boolean;
};

export default function MessageInput({ onSend, connected }: Props) {
  const [input, setInput] = useState("");

  const send = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
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
  );
}
