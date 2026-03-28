"use client";

import dynamic from 'next/dynamic';
import { useEffect, useState, useRef } from 'react';
import { MonitorPlay, ShieldAlert, Cpu, HeartPulse } from 'lucide-react';

// Dynamically import force graph to prevent SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

const mockGraphData = {
  nodes: [
    { id: 'AUTH_GATEWAY_V2', group: 1, val: 20, status: 'critical' },
    { id: 'USER_PROFILE_SVC', group: 2, val: 15, status: 'healthy' },
    { id: 'TRANSACTION_ORCH', group: 2, val: 15, status: 'healthy' },
    { id: 'DATA_LAKE_STREAM', group: 3, val: 10, status: 'warning' },
    { id: 'ANALYTICS_QUERY_API', group: 3, val: 15, status: 'healthy' },
  ],
  links: [
    { source: 'AUTH_GATEWAY_V2', target: 'USER_PROFILE_SVC' },
    { source: 'AUTH_GATEWAY_V2', target: 'TRANSACTION_ORCH' },
    { source: 'TRANSACTION_ORCH', target: 'DATA_LAKE_STREAM' },
    { source: 'ANALYTICS_QUERY_API', target: 'DATA_LAKE_STREAM' },
  ]
};

const mockInventory = [
  { id: 'AUTH_GATEWAY_V2', status: 'critical', latency: '4500ms' },
  { id: 'USER_PROFILE_SVC', status: 'healthy', latency: '12ms' },
  { id: 'TRANSACTION_ORCH', status: 'healthy', latency: '45ms' },
  { id: 'DATA_LAKE_STREAM', status: 'warning', latency: '120ms' },
  { id: 'ANALYTICS_QUERY_API', status: 'healthy', latency: '22ms' },
];

const mockEvents = [
  { time: "15:41:59", tag: "CRIT", msg: "Service AUTH_GATEWAY_V2 reached max retry limit on port 443. Blast radius expanding.", color: "text-cyber-red" },
  { time: "15:41:45", tag: "INFO", msg: "Auto-scaler triggered for CLUSTER_WEST_B: +4 nodes deployed.", color: "text-cyber-cyan" },
  { time: "15:41:30", tag: "AI", msg: "Predictive maintenance suggested for DATA_LAKE shard #09. Risk score: 0.24.", color: "text-cyber-pink" },
  { time: "15:41:22", tag: "INFO", msg: "Health check passed for TRANSACTION_ORCH. Latency normalized to 45ms.", color: "text-cyber-cyan" },
];

export default function TopologyView() {
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial measurement

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const getNodeColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#00E5FF';
      case 'warning': return '#FF6B8B'; // Muted pink for warning based on request
      case 'critical': return '#FF3B5C';
      default: return '#4A5568';
    }
  };

  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono">
      {/* Header */}
      <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
        <div className="flex items-center space-x-3 text-cyber-cyan">
          <MonitorPlay className="w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
            THE DIGITAL SENTINEL
          </h1>
        </div>
        <div className="flex items-center space-x-2 bg-cyber-gray px-3 py-1 rounded border border-cyber-dim">
          <span className="text-sm text-cyber-light font-semibold">OPERATIONAL_NODE</span>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 overflow-hidden">

        {/* Left/Middle Topology & Stats (Span 3 Cols) */}
        <div className="lg:col-span-3 flex flex-col border-r border-cyber-dim p-4 h-[calc(100vh-8rem)]">

          <div className="mb-4">
            <h2 className="text-cyber-cyan text-xl font-bold tracking-widest mb-1 shadow-cyber-cyan">OPERATIONAL_NODE</h2>
            <div className="text-xs text-cyber-dim">CLUSTER: X-RAY-DELTA-9</div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-cyber-dark border-l-2 border-cyber-cyan p-4">
              <div className="text-xs text-cyber-light opacity-70 mb-1">GLOBAL UPTIME</div>
              <div className="text-2xl font-bold text-cyber-light">99.98% <span className="text-cyber-cyan text-sm">▲ 0.02%</span></div>
            </div>
            <div className="bg-cyber-dark border-l-2 border-cyber-pink p-4">
              <div className="text-xs text-cyber-light opacity-70 mb-1">TOTAL INCIDENTS</div>
              <div className="text-2xl font-bold text-cyber-light">12 <span className="text-cyber-pink text-sm">▼ High Priority</span></div>
            </div>
            <div className="bg-cyber-dark border-l-2 border-cyber-dim p-4">
              <div className="text-xs text-cyber-light opacity-70 mb-1">AVG RESOLUTION</div>
              <div className="text-2xl font-bold text-cyber-light">14m 22s <span className="text-cyber-cyan text-sm">Stable</span></div>
            </div>
          </div>

          {/* Topology Graph */}
          <div className="flex-1 bg-cyber-dark border border-cyber-dim relative overflow-hidden" ref={containerRef}>
             <div className="absolute top-4 left-4 z-10 flex items-center text-xs font-bold text-cyber-light tracking-widest">
               <span className="w-2 h-2 bg-cyber-cyan mr-2 inline-block rounded-full shadow-[0_0_8px_#00E5FF]"></span>
               LIVE SERVICE TOPOLOGY
             </div>
             {typeof window !== "undefined" && (
                <ForceGraph2D
                  width={dimensions.width}
                  height={dimensions.height}
                  graphData={mockGraphData}
                  nodeColor={(node: any) => getNodeColor(node.status)}
                  linkColor={() => '#4A5568'}
                  nodeRelSize={8}
                  backgroundColor="#0B0E14"
                  nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const label = node.id;
                    const fontSize = 12/globalScale;
                    ctx.font = `${fontSize}px JetBrains Mono`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

                    ctx.fillStyle = 'rgba(11, 14, 20, 0.8)';
                    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2 - 15/globalScale, bckgDimensions[0], bckgDimensions[1]);

                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = getNodeColor(node.status);

                    // Add glow for critical nodes
                    if(node.status === 'critical') {
                       ctx.shadowBlur = 15;
                       ctx.shadowColor = '#FF3B5C';
                    } else if (node.status === 'healthy') {
                       ctx.shadowBlur = 10;
                       ctx.shadowColor = '#00E5FF';
                    }

                    ctx.fillText(label, node.x, node.y - 15/globalScale);
                    ctx.shadowBlur = 0; // reset

                    // Draw Node geometric shape (square)
                    ctx.fillStyle = 'transparent';
                    ctx.strokeStyle = getNodeColor(node.status);
                    ctx.lineWidth = 2/globalScale;
                    ctx.strokeRect(node.x - 6, node.y - 6, 12, 12);

                    // Inner dot
                    ctx.fillStyle = getNodeColor(node.status);
                    ctx.fillRect(node.x - 2, node.y - 2, 4, 4);
                  }}
                />
             )}
          </div>

        </div>

        {/* Right Sidebar - Service Inventory */}
        <div className="lg:col-span-1 bg-cyber-darker p-4 flex flex-col h-[calc(100vh-8rem)]">
          <div className="flex justify-between items-center mb-4 border-b border-cyber-dim pb-2">
            <h3 className="text-cyber-light font-bold text-sm tracking-widest">SERVICE INVENTORY</h3>
            <span className="bg-cyber-gray text-cyber-red text-xs px-2 py-1 font-bold border border-cyber-red">1 CRITICAL</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
             {mockInventory.map(srv => {
               const bColor = srv.status === 'critical' ? 'border-cyber-red' : srv.status === 'warning' ? 'border-cyber-pink' : 'border-cyber-cyan';
               const dColor = srv.status === 'critical' ? 'bg-cyber-red shadow-[0_0_8px_#FF3B5C]' : srv.status === 'warning' ? 'bg-cyber-pink shadow-[0_0_8px_#FF6B8B]' : 'bg-cyber-cyan shadow-[0_0_8px_#00E5FF]';
               const icon = srv.status === 'critical' ? <ShieldAlert className="w-4 h-4 text-cyber-red" /> : srv.status === 'warning' ? <span className="text-cyber-pink font-bold text-xs">i</span> : <span className="text-cyber-cyan font-bold text-xs">✓</span>;

               return (
                 <div key={srv.id} className={`bg-cyber-dark border-l-4 ${bColor} p-3 flex justify-between items-center`}>
                    <div className="flex items-center space-x-3">
                       <div className={`w-2 h-2 rounded-full ${dColor}`}></div>
                       <div>
                         <div className="text-sm font-bold text-cyber-light">{srv.id}</div>
                         <div className="text-xs text-cyber-dim mt-1">LATENCY: {srv.latency}</div>
                       </div>
                    </div>
                    <div className="bg-cyber-gray rounded-full w-6 h-6 flex items-center justify-center">
                       {icon}
                    </div>
                 </div>
               );
             })}
          </div>

          {/* Bottom Event Stream (Fixed at bottom right) */}
          <div className="mt-4 border-t border-cyber-dim pt-4 flex-none h-64 flex flex-col">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-cyber-cyan font-bold text-xs tracking-widest">REAL-TIME EVENT STREAM</h3>
              <span className="text-xs text-cyber-dim font-mono">15:42:01 UTC</span>
            </div>
            <div className="flex-1 overflow-y-auto font-mono text-xs space-y-3 bg-cyber-dark p-3 border border-cyber-dim rounded">
               {mockEvents.map((evt, idx) => (
                  <div key={idx} className="flex flex-col space-y-1">
                    <div className="flex space-x-2">
                      <span className={`${evt.color} font-bold w-12`}>[{evt.tag}]</span>
                      <span className="text-cyber-dim">{evt.time}</span>
                    </div>
                    <div className="text-cyber-light opacity-80 pl-14 italic leading-relaxed">
                      {evt.msg}
                    </div>
                  </div>
               ))}
            </div>
          </div>

        </div>

      </div>
    </main>
  );
}