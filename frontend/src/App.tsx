
import Bubble from "./components/MessageBubble";
import Status from "./components/Status";
import FileDrop from "./components/FileDrop";
import Header from "./components/Header";
import useAutoScroll from "./hooks/useAutoScroll";
import { useAppContext } from "./context/AppContext";
import MessageInput from "./components/MessageInput";
console.log('App component loaded');

export default function App() {
  const { chat, status, connected, send, uploadFile } = useAppContext();
  useAutoScroll([chat, status]);

  return (
    <div className="h-screen flex flex-col dark:bg-gray-900">
      <Header connected={connected} />
      <main className="flex-1 overflow-y-auto p-4 space-y-3">
        {chat.map((m, i) => (
          <Bubble key={i} role={m.role}>
            {m.content}
          </Bubble>
        ))}
        <Status text={status} />
        <div id="anchor" />
      </main>
      <MessageInput onSend={send} connected={connected} />
      <FileDrop onFile={uploadFile} />
    </div>
  );
}
