"use client";

import { MonitorPlay, Search, BrainCircuit, Activity, Clock } from 'lucide-react';

const mockLogs = [
  { time: '11:22:01.001', svc: 'AUTH_GATEWAY', level: 'INF', msg: 'Incoming request to /api/v2/auth', color: 'border-cyber-cyan text-cyber-cyan' },
  { time: '11:22:01.045', svc: 'USER_PROFILE', level: 'INF', msg: 'Fetching user profile ID: 8945', color: 'border-cyber-cyan text-cyber-cyan' },
  { time: '11:22:01.120', svc: 'TRANSACTION_ORCH', level: 'WRN', msg: 'Payment gateway timeout approaching', color: 'border-cyber-yellow text-cyber-yellow' },
  { time: '11:22:01.150', svc: 'PAYMENT_SVC', level: 'ERR', msg: 'Connection refused to downstream provider (port 5432)', color: 'border-cyber-red text-cyber-red' },
  { time: '11:22:01.155', svc: 'TRANSACTION_ORCH', level: 'ERR', msg: 'Transaction failed, rolling back state', color: 'border-cyber-red text-cyber-red' },
];

const mockTrace = [
  { svc: 'AUTH_GATEWAY', span: 'POST /auth', duration: 155, offset: 0, color: 'bg-cyber-cyan' },
  { svc: 'USER_PROFILE', span: 'GET /user/:id', duration: 45, offset: 10, color: 'bg-cyber-dim' },
  { svc: 'TRANSACTION_ORCH', span: 'POST /tx/init', duration: 100, offset: 55, color: 'bg-cyber-yellow' },
  { svc: 'PAYMENT_SVC', span: 'POST /provider', duration: 10, offset: 145, color: 'bg-cyber-red' },
];

export default function TracesView() {
  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono">
      {/* Header */}
      <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
        <div className="flex items-center space-x-3 text-cyber-cyan">
          <MonitorPlay className="w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
            DISTRIBUTED TRACING
          </h1>
        </div>

        <div className="flex-1 max-w-2xl ml-8">
           <div className="flex items-center bg-cyber-dark border border-cyber-dim px-3 py-2 text-sm focus-within:border-cyber-cyan transition-colors">
              <Search className="w-4 h-4 text-cyber-dim mr-2" />
              <input
                 type="text"
                 defaultValue='{service="TRANSACTION_ORCH"} |= "error"'
                 className="bg-transparent border-none outline-none text-cyber-light w-full font-mono placeholder-cyber-dim"
                 placeholder="LogQL Query..."
              />
           </div>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-hidden pb-20">

        {/* Left Column - Log Stream */}
        <div className="bg-cyber-dark border border-cyber-dim p-4 flex flex-col h-[calc(100vh-10rem)]">
           <div className="text-xs text-cyber-cyan font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
             <Activity className="w-4 h-4 mr-2" />
             LOG STREAM
           </div>

           <div className="flex-1 overflow-y-auto space-y-2 font-mono text-xs pr-2">
             {mockLogs.map((log, i) => (
                <div key={i} className={`border-l-2 ${log.color} bg-cyber-darker p-2 flex hover:bg-cyber-gray/30 cursor-pointer`}>
                   <div className="w-24 text-cyber-dim shrink-0">{log.time}</div>
                   <div className="w-12 font-bold shrink-0">{log.level}</div>
                   <div className="w-40 text-cyber-light opacity-80 shrink-0 truncate pr-2">{log.svc}</div>
                   <div className="text-cyber-light">{log.msg}</div>
                </div>
             ))}
           </div>
        </div>

        {/* Right Column - Trace Explorer & Metadata */}
        <div className="flex flex-col space-y-4 h-[calc(100vh-10rem)]">

           {/* Trace Explorer */}
           <div className="bg-cyber-dark border border-cyber-dim p-4 flex-1 flex flex-col">
              <div className="text-xs text-cyber-cyan font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center justify-between">
                 <div className="flex items-center"><Clock className="w-4 h-4 mr-2" /> TRACE EXPLORER</div>
                 <span className="text-cyber-dim font-mono">TRACE_ID: 9a8b7c6d5e4f3a2b</span>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 relative">
                 {/* Waterfall grid lines */}
                 <div className="absolute inset-0 flex justify-between pointer-events-none opacity-10">
                    {[1,2,3,4,5].map(i => <div key={i} className="border-l border-cyber-light h-full"></div>)}
                 </div>

                 <div className="space-y-4 pt-2">
                    {mockTrace.map((trace, i) => (
                       <div key={i} className="relative h-12 group">
                          <div className="flex justify-between text-[10px] text-cyber-dim mb-1">
                             <span className="font-bold text-cyber-light">{trace.svc}</span>
                             <span>{trace.span} ({trace.duration}ms)</span>
                          </div>
                          <div
                             className={`h-4 ${trace.color} relative opacity-80 group-hover:opacity-100 transition-opacity`}
                             style={{ width: `${(trace.duration / 155) * 100}%`, marginLeft: `${(trace.offset / 155) * 100}%` }}
                          ></div>
                       </div>
                    ))}
                 </div>
              </div>
           </div>

           {/* Metadata Details & AI RCA */}
           <div className="grid grid-cols-2 gap-4 h-48">
              <div className="bg-cyber-darker border border-cyber-dim p-4 overflow-y-auto">
                 <div className="text-xs text-cyber-dim font-bold tracking-widest mb-2">SPAN METADATA</div>
                 <pre className="text-[10px] text-cyber-light opacity-70 font-mono">
{`{
  "trace_id": "9a8b7c6d5e4f3a2b",
  "span_id": "f4e3d2c1b0a9",
  "service": "PAYMENT_SVC",
  "error": true,
  "http.status_code": 500,
  "db.statement": "SELECT * FROM..."
}`}
                 </pre>
              </div>

              <div className="bg-cyber-darker border border-cyber-pink p-4 shadow-[0_0_15px_rgba(255,107,139,0.15)] overflow-y-auto">
                 <div className="flex items-center space-x-2 mb-2 text-cyber-pink">
                    <BrainCircuit className="w-4 h-4" />
                    <span className="text-xs font-bold tracking-widest">AI ROOT CAUSE</span>
                 </div>
                 <p className="text-xs text-cyber-light opacity-90 leading-relaxed mb-2">
                    Log embeddings indicate a high correlation with network partition. Connection to downstream provider &apos;pg-cluster-01&apos; severed.
                 </p>
                 <div className="text-[10px] border-l-2 border-cyber-pink pl-2 py-1 text-cyber-dim font-mono">
                   CONFIDENCE: 98.7%
                 </div>
              </div>
           </div>

        </div>

      </div>
    </main>
  );
}