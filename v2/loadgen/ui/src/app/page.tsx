import Header from '@/components/Header';
import TrafficControl from '@/components/TrafficControl';
import LiveStats from '@/components/LiveStats';
import ChaosGrid from '@/components/ChaosGrid';
import ActionLog from '@/components/ActionLog';

export default function Home() {
  return (
    <main className="min-h-screen bg-cyber-darker text-cyber-light flex flex-col font-mono selection:bg-cyber-cyan selection:text-cyber-darker">
      <Header />

      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 overflow-y-auto">

        {/* Left Column */}
        <div className="lg:col-span-1 space-y-6 flex flex-col">
          <TrafficControl />
          <LiveStats />
        </div>

        {/* Right Column */}
        <div className="lg:col-span-3 flex flex-col space-y-6">
          <ChaosGrid />
          <ActionLog />
        </div>

      </div>
    </main>
  );
}