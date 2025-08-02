
import { Link } from "react-router-dom";
import { ThemeToggler } from "./ThemeToggler";
import { useAppContext } from "../context/AppContext";

export function Navbar() {
  const { connected } = useAppContext();
  return (
    <nav className="flex items-center justify-between p-4 bg-card text-card-foreground border-b">
      <div className="flex items-center space-x-4">
        <Link to="/" className="text-lg font-semibold">
          IB Assistant
        </Link>
      </div>
      <div className="flex items-center space-x-4">
        <Link to="/grafana" className="px-4 py-2 hover:bg-muted rounded">
          📊 Мониторинг
        </Link>
        <ThemeToggler />
        <span className={`ml-2 text-xs px-2 py-1 rounded ${connected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {connected ? 'Бэкенд: онлайн' : 'Бэкенд: нет связи'}
        </span>
      </div>
    </nav>
  );
}
