"use client";

import { MonitorPlay, BrainCircuit, Activity, ShieldAlert } from 'lucide-react';

const mockIncidents = [
  { id: 'INC-902', time: '14:22 UTC', svc: 'PYMT_GATEWAY', rootCause: 'Database connection pool exhausted', confidence: 98.4, status: 'RESOLVED' },
  { id: 'INC-903', time: '15:10 UTC', svc: 'CART_ENGINE', rootCause: 'OOM Killed (Memory limit exceeded)', confidence: 99.1, status: 'RECOVERING' },
];

export default function AiRcaView() {
  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono">
      {/* Header */}
      <header className="flex justify-between items-center py-4 px-6 border-b border-cyber-gray bg-cyber-dark">
        <div className="flex items-center space-x-3 text-cyber-cyan">
          <MonitorPlay className="w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-widest" style={{ textShadow: "0 0 10px #00E5FF" }}>
            AI ROOT CAUSE INTELLIGENCE
          </h1>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-hidden pb-20">

        {/* Left Column - Active Incident Details */}
        <section className="bg-cyber-dark border border-cyber-pink p-6 rounded-md shadow-[0_0_20px_rgba(255,107,139,0.1)] flex flex-col h-full">
          <h2 className="text-cyber-pink font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
            <ShieldAlert className="w-5 h-5 text-cyber-pink mr-2" />
            ACTIVE INCIDENT: INC-904
          </h2>

          <div className="flex-1 overflow-y-auto space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-cyber-darker border border-cyber-dim p-3">
                <div className="text-xs text-cyber-dim mb-1">IMPACTED SERVICE</div>
                <div className="text-lg font-bold text-cyber-red">AUTH_GATEWAY_V2</div>
              </div>
              <div className="bg-cyber-darker border border-cyber-dim p-3">
                <div className="text-xs text-cyber-dim mb-1">DETECTION TIME</div>
                <div className="text-lg font-bold text-cyber-light">15:41:59 UTC</div>
              </div>
            </div>

            <div className="bg-cyber-darker border-l-4 border-cyber-pink p-4 relative overflow-hidden">
              <div className="flex items-center space-x-2 mb-2 text-cyber-pink">
                <BrainCircuit className="w-5 h-5" />
                <span className="text-sm font-bold tracking-widest">AI INFERENCE ENGINE</span>
              </div>
              <p className="text-sm text-cyber-light opacity-90 leading-relaxed mb-4">
                Analysis of logs and metrics indicates a high probability of SSL certificate expiration leading to maximum retry limit being reached. Blast radius expanding to dependent downstream services.
              </p>
              <div className="bg-cyber-gray p-2 text-sm text-cyber-cyan font-mono mb-2">
                Confidence Score: <span className="font-bold">96.8%</span>
              </div>
              <div className="bg-cyber-gray p-2 text-sm text-cyber-yellow font-mono">
                Suggested Action: Renew SSL cert for cluster WEST_B and restart gateway pods.
              </div>
            </div>

            <div className="flex space-x-4 pt-4">
              <button className="flex-1 bg-cyber-pink text-cyber-darker font-bold py-3 px-4 flex items-center justify-center transition-colors shadow-[0_0_15px_rgba(255,107,139,0.3)]">
                EXECUTE AUTO-REMEDIATION
              </button>
            </div>
          </div>
        </section>

        {/* Right Column - Incident History */}
        <section className="bg-cyber-dark border border-cyber-dim p-6 rounded-md h-full flex flex-col">
          <h2 className="text-cyber-cyan font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
            <Activity className="w-5 h-5 text-cyber-cyan mr-2" />
            INCIDENT HISTORY
          </h2>

          <div className="flex-1 overflow-y-auto space-y-4">
            {mockIncidents.map((inc) => (
              <div key={inc.id} className="bg-cyber-darker border border-cyber-dim p-4 group hover:border-cyber-cyan transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-cyber-cyan font-bold">{inc.id}</span>
                    <span className="text-xs text-cyber-dim">{inc.time}</span>
                  </div>
                  <span className={`text-xs px-2 py-1 font-bold ${inc.status === 'RESOLVED' ? 'bg-cyber-gray text-cyber-cyan' : 'bg-cyber-gray text-cyber-yellow'}`}>
                    {inc.status}
                  </span>
                </div>

                <div className="mb-2">
                  <div className="text-xs text-cyber-dim mb-1">SERVICE: {inc.svc}</div>
                  <div className="text-sm text-cyber-light">{inc.rootCause}</div>
                </div>

                <div className="flex items-center justify-between text-xs mt-3 pt-2 border-t border-cyber-gray">
                  <span className="text-cyber-pink font-mono">AI Conf: {inc.confidence}%</span>
                  <button className="text-cyber-cyan hover:underline">VIEW DETAILS &rarr;</button>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </main>
  );
}