import ThemeToggle from "./ThemeToggle";
import logo from '../assets/logo.svg';
import ConnectionStatus from "./ConnectionStatus"

export default function Header({ connected }: { connected: boolean }) {
  return (
    <header className="flex items-center justify-between p-3 bg-brand text-white">
      <div className="flex items-center gap-2">
        <img src={logo} className="h-8 w-8"/>
        <span className="font-semibold text-lg">IB Assistant</span>
      </div>
      <div className="flex items-center gap-4">
        <ConnectionStatus connected={connected} />
        <ThemeToggle/>
      </div>
    </header>
  )
}
