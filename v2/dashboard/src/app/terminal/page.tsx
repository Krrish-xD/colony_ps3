"use client";

import { MonitorPlay, Terminal } from 'lucide-react';

const mockLogs = [
  { time: "14:22:01", level: "COMMAND:", text: "Executed load test profile: SPIKE_TEST", color: "text-cyber-cyan" },
  { time: "14:22:15", level: "CHAOS:", text: "Injected artificial latency (500ms) into PYMT_GATEWAY", color: "text-cyber-yellow" },
  { time: "14:22:30", level: "AI_INSIGHT:", text: "Anomaly detected in transaction flow. Root cause analysis initiated.", color: "text-cyber-pink" },
  { time: "14:23:00", level: "COMMAND:", text: "Hard kill signal sent to CART_ENGINE container", color: "text-cyber-red" },
  { time: "14:23:05", level: "SYSTEM:", text: "CART_ENGINE container terminated (SIGKILL)", color: "text-cyber-light" },
];

export default function TerminalView() {
  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono">
      {/* Header */}
      <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
        <div className="flex items-center space-x-3 text-cyber-cyan">
          <MonitorPlay className="w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
            SYSTEM TERMINAL
          </h1>
        </div>
      </header>

      {/* Terminal Content */}
      <div className="flex-1 p-6 overflow-hidden">
        <section className="bg-black border border-cyber-dim p-4 rounded-md h-full flex flex-col">
          <h2 className="text-cyber-dim font-bold tracking-widest mb-2 border-b border-cyber-dim pb-2 flex items-center text-xs">
            <Terminal className="w-4 h-4 mr-2" />
            SYSTEM ACTION LOG - FULL STREAM
          </h2>

          <div className="flex-1 overflow-y-auto font-mono text-sm space-y-2 mt-2">
            {mockLogs.map((log, idx) => (
              <div key={idx} className="flex">
                <span className="text-cyber-dim mr-3">[{log.time}]</span>
                <span className={`${log.color} font-bold mr-2 w-32`}>{log.level}</span>
                <span className="text-cyber-light opacity-80">{log.text}</span>
              </div>
            ))}
            <div className="flex mt-2 animate-pulse">
              <span className="text-cyber-cyan mr-2">&gt;</span>
              <span className="text-cyber-dim">_</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}