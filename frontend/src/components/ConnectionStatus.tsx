export default function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-white/80">
        {connected ? "Онлайн" : "Нет соединения"}
      </span>
      <div 
        className={`w-3 h-3 rounded-full transition-colors ${connected ? "bg-green-400" : "bg-red-400"}`}
        title={connected ? "Соединение установлено" : "Соединение потеряно, попытка переподключения..."}
      />
    </div>
  )
}
