export default function Grafana() {
  const src = `${import.meta.env.VITE_GRAFANA_URL}/d/ib-overview/ib-assistant-overview?orgId=1&kiosk&theme=light`;
  return (
    <div className="bg-white border rounded-lg shadow w-full h-[calc(100vh-70px)]">
      <iframe src={src} className="w-full h-full rounded-lg" />
    </div>
  );
}
