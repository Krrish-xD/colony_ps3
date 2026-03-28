import { User, MonitorPlay } from 'lucide-react';

export default function Header() {
  return (
    <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
      <div className="flex items-center space-x-3 text-cyber-cyan">
        <MonitorPlay className="w-8 h-8" />
        <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
          THE DIGITAL SENTINEL
        </h1>
      </div>
      <div className="flex items-center space-x-2 bg-cyber-gray px-3 py-1 rounded border border-cyber-dim">
        <User className="w-5 h-5 text-cyber-light" />
        <span className="text-sm text-cyber-light font-semibold">OP_ADMIN</span>
      </div>
    </header>
  );
}