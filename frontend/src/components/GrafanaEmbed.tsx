export default function Grafana(){
  return (
    <iframe
      src={`${import.meta.env.VITE_GRAFANA_URL}/d/ib-overview/ib-assistant-overview?orgId=1&kiosk`}
      className="w-full h-screen border-0"
    />
  );
}
