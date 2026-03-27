import dynamic from 'next/dynamic';

// Dynamically import the ForceGraph component to disable SSR
// react-force-graph requires the window object to render
const TopologyGraph = dynamic(
  () => import('@/components/TopologyGraph'),
  { ssr: false }
);

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between">
      <TopologyGraph />
    </main>
  );
}
