
import { Link, useLocation } from "react-router-dom";
import { ThemeToggler } from "./ThemeToggler";
import { useAppContext } from "../context/AppContext";
import logo from '../assets/logo.svg';

export function Navbar() {
  const { connected } = useAppContext();
  const location = useLocation();
  
  return (
    <nav className="flex items-center justify-between p-4 bg-brand text-white shadow-md">
      <div className="flex items-center space-x-4">
        <Link to="/" className="flex items-center gap-2 text-lg font-semibold hover:opacity-80">
          <img src={logo} className="h-8 w-8" alt="IB Assistant" />
          IB Assistant
        </Link>
      </div>
      <div className="flex items-center space-x-4">
        {location.pathname !== '/' && (
          <Link 
            to="/" 
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded transition-colors"
          >
            🏠 Главная
          </Link>
        )}
        <Link 
          to="/grafana" 
          className={`px-4 py-2 hover:bg-white/20 rounded transition-colors ${
            location.pathname === '/grafana' ? 'bg-white/20' : ''
          }`}
        >
          📊 Мониторинг
        </Link>
        <Link 
          to="/logs" 
          className={`px-4 py-2 hover:bg-white/20 rounded transition-colors ${
            location.pathname === '/logs' ? 'bg-white/20' : ''
          }`}
        >
          📋 Логи
        </Link>
        <ThemeToggler />
        <span className={`ml-2 text-xs px-2 py-1 rounded ${
          connected ? 'bg-green-500/20 text-green-200' : 'bg-red-500/20 text-red-200'
        }`}>
          {connected ? 'Онлайн' : 'Офлайн'}
        </span>
      </div>
    </nav>
  );
}
