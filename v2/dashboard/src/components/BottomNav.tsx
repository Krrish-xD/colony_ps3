"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { TerminalSquare, LineChart, Network, ListTree, BrainCircuit } from 'lucide-react';

export default function BottomNav() {
  const pathname = usePathname();

  const tabs = [
    { name: 'TERMINAL', path: '/terminal', icon: TerminalSquare },
    { name: 'METRICS', path: '/metrics', icon: LineChart },
    { name: 'TOPOLOGY', path: '/', icon: Network },
    { name: 'TRACES', path: '/traces', icon: ListTree },
    { name: 'AI RCA', path: '/ai-rca', icon: BrainCircuit },
  ];

  return (
    <nav className="fixed bottom-0 w-full bg-cyber-dark border-t border-cyber-dim h-16 flex justify-center items-center px-4 z-50">
      <div className="flex space-x-2 md:space-x-8">
        {tabs.map((tab) => {
          const isActive = pathname === tab.path;
          const Icon = tab.icon;

          return (
            <Link
              key={tab.name}
              href={tab.path}
              className={`flex flex-col items-center justify-center w-24 h-14 transition-all duration-300 border-t-2 ${
                isActive
                  ? 'border-cyber-cyan text-cyber-cyan bg-cyber-darker shadow-[0_-5px_15px_-5px_rgba(0,229,255,0.3)]'
                  : 'border-transparent text-cyber-dim hover:text-cyber-light hover:bg-cyber-darker'
              }`}
            >
              <Icon className={`w-5 h-5 mb-1 ${isActive ? 'animate-pulse' : ''}`} />
              <span className="text-[10px] font-bold tracking-widest">[ {tab.name} ]</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}