"use client";

import { useState } from 'react';
import { Play, Square } from 'lucide-react';

export default function TrafficControl() {
  const [users, setUsers] = useState(100);
  const [interval, setIntervalVal] = useState(10);
  const [active, setActive] = useState(false);

  const handleExecute = () => {
    setActive(true);
    // TODO: Wire up to Locust later
  };

  const handleStopAll = () => {
    setActive(false);
    // TODO: Wire up to Locust later
  };

  return (
    <section className="bg-cyber-dark border border-cyber-dim p-6 rounded-md">
      <h2 className="text-cyber-cyan font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
        <span className="w-2 h-2 bg-cyber-cyan mr-2 inline-block"></span>
        TRAFFIC CONTROL
      </h2>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="flex flex-col space-y-2">
          <label className="text-xs text-cyber-light opacity-70">SPAWN X USERS</label>
          <input
            type="number"
            value={users}
            onChange={(e) => setUsers(Number(e.target.value))}
            className="bg-cyber-darker border border-cyber-dim p-2 text-cyber-cyan font-mono focus:border-cyber-cyan focus:outline-none w-full"
          />
        </div>
        <div className="flex flex-col space-y-2">
          <label className="text-xs text-cyber-light opacity-70">SPAWN INTERVAL (ms)</label>
          <input
            type="number"
            value={interval}
            onChange={(e) => setIntervalVal(Number(e.target.value))}
            className="bg-cyber-darker border border-cyber-dim p-2 text-cyber-cyan font-mono focus:border-cyber-cyan focus:outline-none w-full"
          />
        </div>
      </div>

      <div className="bg-cyber-darker border border-cyber-dim p-4 mb-6 text-center rounded">
        <div className="text-xs text-cyber-light opacity-70 mb-1">SESSION COUNTDOWN</div>
        <div className="text-4xl font-bold font-mono text-cyber-cyan" style={{ textShadow: "0 0 10px rgba(0, 229, 255, 0.5)" }}>
          {active ? "04:59:32" : "00:00:00"}
        </div>
      </div>

      <div className="flex space-x-4">
        <button
          onClick={handleExecute}
          className="flex-1 bg-transparent border border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan hover:text-cyber-darker font-bold py-3 px-4 flex items-center justify-center transition-colors shadow-[0_0_10px_rgba(0,229,255,0.2)]"
        >
          <Play className="w-4 h-4 mr-2" fill="currentColor" />
          EXECUTE
        </button>
        <button
          onClick={handleStopAll}
          className="flex-1 bg-transparent border border-cyber-red text-cyber-red hover:bg-cyber-red hover:text-white font-bold py-3 px-4 flex items-center justify-center transition-colors shadow-[0_0_10px_rgba(255,59,92,0.2)]"
        >
          <Square className="w-4 h-4 mr-2" fill="currentColor" />
          STOP ALL
        </button>
      </div>
    </section>
  );
}