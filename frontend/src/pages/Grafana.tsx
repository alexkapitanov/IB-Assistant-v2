export default function Grafana() {
  const grafanaUrl = import.meta.env.VITE_GRAFANA_URL || "/grafana";
  const src = `${grafanaUrl}/d/ib-overview/ib-assistant-overview?kiosk&refresh=5s&theme=light`;
  
  return (
    <div className="h-full bg-white">
      <div className="p-4 border-b bg-gray-50">
        <h1 className="text-2xl font-bold text-gray-800">Мониторинг системы</h1>
        <p className="text-gray-600 mt-1">Дашборд метрик и производительности IB Assistant</p>
      </div>
      <div className="h-[calc(100%-80px)]">
        <iframe
          src={src}
          className="w-full h-full border-0"
          title="IB Assistant Dashboard"
          loading="lazy"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}
