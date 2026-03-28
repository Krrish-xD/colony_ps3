"use client";

import { MonitorPlay, Settings2, BrainCircuit } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line
} from 'recharts';

const latencyData = [
  { time: '10:00', p50: 10, p95: 25, p99: 45 },
  { time: '10:05', p50: 12, p95: 28, p99: 50 },
  { time: '10:10', p50: 15, p95: 35, p99: 80 },
  { time: '10:15', p50: 25, p95: 140, p99: 450 },
  { time: '10:20', p50: 18, p95: 45, p99: 95 },
  { time: '10:25', p50: 14, p95: 30, p99: 55 },
];

const trafficData = [
  { time: '10:00', reqs: 1200, errors: 2 },
  { time: '10:05', reqs: 1350, errors: 5 },
  { time: '10:10', reqs: 1800, errors: 15 },
  { time: '10:15', reqs: 4500, errors: 450 },
  { time: '10:20', reqs: 1400, errors: 12 },
  { time: '10:25', reqs: 1250, errors: 3 },
];

const lstmData = [
  { time: '10:00', actual: 1200, forecast: 1150 },
  { time: '10:05', actual: 1350, forecast: 1300 },
  { time: '10:10', actual: 1800, forecast: 1750 },
  { time: '10:15', actual: 4500, forecast: 2000 }, // Spike!
  { time: '10:20', forecast: 2100 },
  { time: '10:25', forecast: 2050 },
];

const metadata = [
  { srv: 'AUTH_GATEWAY_V2', uptime: '99.99%', cpu: '500m', mem: '256Mi' },
  { srv: 'USER_PROFILE_SVC', uptime: '99.95%', cpu: '200m', mem: '128Mi' },
  { srv: 'TRANSACTION_ORCH', uptime: '99.98%', cpu: '1000m', mem: '512Mi' },
];

export default function MetricsView() {
  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono">
      {/* Header */}
      <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
        <div className="flex items-center space-x-3 text-cyber-cyan">
          <MonitorPlay className="w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
            SYSTEM LATENCY & THROUGHPUT
          </h1>
        </div>
        <div className="flex items-center space-x-4">
          <select className="bg-cyber-gray border border-cyber-dim text-cyber-cyan px-3 py-1 text-sm outline-none">
            <option>ALL_SERVICES</option>
            <option>AUTH_GATEWAY_V2</option>
            <option>TRANSACTION_ORCH</option>
          </select>
          <div className="flex space-x-1 border border-cyber-dim bg-cyber-gray rounded p-1">
            {['1H', '6H', '24H', '7D'].map(t => (
               <button key={t} className={`px-2 py-0.5 text-xs font-bold ${t === '1H' ? 'bg-cyber-cyan text-cyber-dark' : 'text-cyber-dim hover:text-cyber-light'}`}>
                 {t}
               </button>
            ))}
          </div>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-y-auto pb-20">

        {/* Main Charts (Left Span 2) */}
        <div className="lg:col-span-2 flex flex-col space-y-4">

           {/* Latency Percentiles */}
           <div className="bg-cyber-dark border border-cyber-dim p-4 h-64">
             <div className="text-xs text-cyber-cyan font-bold tracking-widest mb-2 border-b border-cyber-dim pb-2 flex items-center">
               <span className="w-2 h-2 bg-cyber-cyan mr-2 inline-block"></span> LATENCY PERCENTILES
             </div>
             <ResponsiveContainer width="100%" height="85%">
                <LineChart data={latencyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2A3143" vertical={false} />
                  <XAxis dataKey="time" stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <YAxis stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0B0E14', borderColor: '#4A5568' }} />
                  <Line type="monotone" dataKey="p99" stroke="#FF3B5C" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="p95" stroke="#FFD166" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="p50" stroke="#00E5FF" strokeWidth={2} dot={false} />
                </LineChart>
             </ResponsiveContainer>
           </div>

           {/* Traffic Volume vs Errors */}
           <div className="bg-cyber-dark border border-cyber-dim p-4 h-64">
             <div className="text-xs text-cyber-cyan font-bold tracking-widest mb-2 border-b border-cyber-dim pb-2 flex items-center">
               <span className="w-2 h-2 bg-cyber-cyan mr-2 inline-block"></span> TRAFFIC VOLUME vs ERRORS
             </div>
             <ResponsiveContainer width="100%" height="85%">
                <AreaChart data={trafficData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2A3143" vertical={false} />
                  <XAxis dataKey="time" stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <YAxis stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0B0E14', borderColor: '#4A5568' }} />
                  <Area type="monotone" dataKey="reqs" stroke="#00E5FF" fill="#00E5FF" fillOpacity={0.1} />
                  <Area type="monotone" dataKey="errors" stroke="#FF3B5C" fill="#FF3B5C" fillOpacity={0.3} />
                </AreaChart>
             </ResponsiveContainer>
           </div>

           {/* LSTM Traffic Forecast */}
           <div className="bg-cyber-dark border border-cyber-dim p-4 h-64">
             <div className="text-xs text-cyber-pink font-bold tracking-widest mb-2 border-b border-cyber-dim pb-2 flex items-center">
               <BrainCircuit className="w-4 h-4 text-cyber-pink mr-2" /> LSTM TRAFFIC FORECAST
             </div>
             <ResponsiveContainer width="100%" height="85%">
                <LineChart data={lstmData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2A3143" vertical={false} />
                  <XAxis dataKey="time" stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <YAxis stroke="#4A5568" tick={{ fill: '#E2E8F0', fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0B0E14', borderColor: '#4A5568' }} />
                  <Line type="monotone" dataKey="actual" stroke="#00E5FF" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="forecast" stroke="#FF6B8B" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                </LineChart>
             </ResponsiveContainer>
           </div>

        </div>

        {/* Right Sidebar */}
        <div className="lg:col-span-1 flex flex-col space-y-4">

           {/* AI RCA Intel Panel */}
           <div className="bg-cyber-darker border border-cyber-pink p-4 shadow-[0_0_15px_rgba(255,107,139,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-cyber-pink text-cyber-darker text-[10px] font-bold px-2 py-1">AI INSIGHT</div>
              <div className="flex items-center space-x-3 mb-3 mt-2">
                 <BrainCircuit className="w-6 h-6 text-cyber-pink" />
                 <h3 className="text-cyber-pink font-bold tracking-widest">ANOMALY DETECTED</h3>
              </div>
              <p className="text-sm text-cyber-light opacity-90 leading-relaxed mb-3">
                 Traffic spike detected at 10:15 deviates 300% from LSTM prediction. Correlated with elevated P99 latency in TRANSACTION_ORCH.
              </p>
              <div className="text-xs border-l-2 border-cyber-pink pl-2 py-1 text-cyber-dim font-mono">
                CONFIDENCE: 94.2%<br/>
                SUGGESTED ACTION: Auto-Scale
              </div>
           </div>

           {/* Cluster Service Metadata */}
           <div className="bg-cyber-dark border border-cyber-dim p-4 flex-1">
             <div className="text-xs text-cyber-light opacity-70 mb-4 border-b border-cyber-dim pb-2 flex items-center">
               <Settings2 className="w-4 h-4 mr-2" /> CLUSTER METADATA
             </div>

             <div className="overflow-x-auto">
               <table className="w-full text-left text-xs font-mono">
                 <thead className="text-cyber-dim border-b border-cyber-gray">
                   <tr>
                     <th className="pb-2">SERVICE</th>
                     <th className="pb-2">UPTIME</th>
                     <th className="pb-2">CPU_LIMIT</th>
                     <th className="pb-2">MEM_LIMIT</th>
                   </tr>
                 </thead>
                 <tbody>
                   {metadata.map(m => (
                     <tr key={m.srv} className="border-b border-cyber-gray/50 hover:bg-cyber-gray/20 transition-colors">
                       <td className="py-3 text-cyber-cyan font-bold">{m.srv}</td>
                       <td className="py-3 text-cyber-light">{m.uptime}</td>
                       <td className="py-3 text-cyber-dim">{m.cpu}</td>
                       <td className="py-3 text-cyber-dim">{m.mem}</td>
                     </tr>
                   ))}
                 </tbody>
               </table>
             </div>
           </div>

        </div>

      </div>
    </main>
  );
}