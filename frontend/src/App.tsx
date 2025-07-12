import { useState, useEffect } from 'react';

function App() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [msg, setMsg] = useState("");
  const [chat, setChat] = useState<string[]>([]);

  useEffect(() => {
    const w = new WebSocket("ws://localhost:8000/ws");
    setWs(w);
    w.onmessage = e => setChat(c => [...c, e.data]);
    return () => { w.close(); };
  }, []);

  return (
    <div>
      {chat.map((m, i) => <p key={i}>{m}</p>)}
      <input
        value={msg}
        onChange={e => setMsg(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter") {
            ws?.send(msg);
            setMsg("");
          }
        }}
      />
    </div>
  );
}

export default App;
