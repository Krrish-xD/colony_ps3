"use client";

import { ShieldAlert, Cpu, HeartPulse } from 'lucide-react';

const mockServices = [
  { id: 'AUTH_SRV_01', status: 'healthy', latency: '45ms' },
  { id: 'PYMT_GATEWAY', status: 'degraded', latency: '420ms' },
  { id: 'USER_PROFILE', status: 'healthy', latency: '22ms' },
  { id: 'CART_ENGINE', status: 'critical', latency: 'ERR' },
  { id: 'INVENTORY_DB', status: 'healthy', latency: '15ms' },
];

export default function ChaosGrid() {
  const getStatusColor = (status: string) => {
    switch(status) {
      case 'healthy': return 'bg-cyber-cyan shadow-[0_0_8px_#00E5FF]';
      case 'degraded': return 'bg-cyber-yellow shadow-[0_0_8px_#FFD166]';
      case 'critical': return 'bg-cyber-red shadow-[0_0_8px_#FF3B5C]';
      default: return 'bg-cyber-dim';
    }
  };

  return (
    <section className="bg-cyber-dark border border-cyber-dim p-6 rounded-md col-span-2">
      <h2 className="text-cyber-red font-bold tracking-widest mb-4 border-b border-cyber-dim pb-2 flex items-center">
        <ShieldAlert className="w-4 h-4 text-cyber-red mr-2" />
        CHAOS CONTROL GRID
      </h2>

      <div className="grid grid-cols-2 gap-4">
        {mockServices.map((srv) => (
          <div key={srv.id} className="bg-cyber-darker border border-cyber-dim p-4 flex justify-between items-center group hover:border-cyber-cyan transition-colors">

            <div className="flex items-center space-x-4">
              <div className={`w-3 h-3 rounded-full ${getStatusColor(srv.status)}`} />
              <div>
                <div className="font-bold text-cyber-light flex items-center">
                  <Cpu className="w-3 h-3 mr-2 text-cyber-dim" />
                  {srv.id}
                </div>
                <div className="text-xs text-cyber-dim font-mono mt-1">LATENCY: {srv.latency}</div>
              </div>
            </div>

            <div className="flex space-x-2">
              <button className="text-xs bg-transparent border border-cyber-red text-cyber-red hover:bg-cyber-red hover:text-white px-3 py-1 font-bold transition-colors flex items-center">
                KILL
              </button>
              <button className="text-xs bg-transparent border border-cyber-cyan text-cyber-cyan hover:bg-cyber-cyan hover:text-cyber-darker px-3 py-1 font-bold transition-colors flex items-center">
                <HeartPulse className="w-3 h-3 mr-1" /> RECOVER
              </button>
            </div>

          </div>
        ))}
      </div>
    </section>
  );
}