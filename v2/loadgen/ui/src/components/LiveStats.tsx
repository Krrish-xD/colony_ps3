"use client";

import { Activity } from 'lucide-react';
import { BarChart, Bar, ResponsiveContainer, XAxis, Tooltip } from 'recharts';

const latencyData = [
  { name: 'P50', value: 45 },
  { name: 'P75', value: 65 },
  { name: 'P90', value: 120 },
  { name: 'P95', value: 240 },
  { name: 'P99', value: 450 },
];

export default function LiveStats() {
  return (
    <section className="bg-cyber-dark border border-cyber-dim p-6 rounded-md">
      <h2 className="text-cyber-cyan font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
        <Activity className="w-4 h-4 text-cyber-cyan mr-2" />
        LIVE STATS
      </h2>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-cyber-darker border border-cyber-dim p-4 text-center">
          <div className="text-xs text-cyber-light opacity-70 mb-1">RPS</div>
          <div className="text-2xl font-bold text-cyber-cyan">12.4k</div>
        </div>
        <div className="bg-cyber-darker border border-cyber-red p-4 text-center">
          <div className="text-xs text-cyber-light opacity-70 mb-1">ERROR %</div>
          <div className="text-2xl font-bold text-cyber-red">0.02%</div>
        </div>
        <div className="bg-cyber-darker border border-cyber-dim p-4 text-center">
          <div className="text-xs text-cyber-light opacity-70 mb-1">AVG LATENCY</div>
          <div className="text-2xl font-bold text-cyber-cyan">42ms</div>
        </div>
      </div>

      <div className="bg-cyber-darker border border-cyber-dim p-4">
        <div className="text-xs text-cyber-light opacity-70 mb-4">AGGREGATED LATENCY DISTRIBUTION</div>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={latencyData}>
              <XAxis dataKey="name" stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
              <Tooltip
                cursor={{ fill: 'rgba(0, 229, 255, 0.1)' }}
                contentStyle={{ backgroundColor: '#0B0E14', borderColor: '#00E5FF' }}
              />
              <Bar dataKey="value" fill="#00E5FF" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}