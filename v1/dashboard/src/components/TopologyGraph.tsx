"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods, NodeObject, LinkObject } from 'react-force-graph-2d';

// Define the shape of our nodes and links
interface GraphNode extends NodeObject {
  id: string;
  name: string;
  val: number;
  color: string;
  status: 'healthy' | 'failing' | 'recovering';
}

interface GraphLink extends LinkObject {
  source: string;
  target: string;
  value: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export default function TopologyGraph() {
  const fgRef = useRef<ForceGraphMethods>();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [logs, setLogs] = useState<{ timestamp: string, message: string, type: 'info' | 'error' | 'success' }[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Handle resizing
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const addLog = useCallback((message: string, type: 'info' | 'error' | 'success' = 'info') => {
    setLogs(prev => {
      const newLogs = [...prev, { timestamp: new Date().toLocaleTimeString(), message, type }];
      // Keep last 50 logs
      return newLogs.slice(-50);
    });
  }, []);

  // Fetch initial topology
  useEffect(() => {
    async function fetchTopology() {
      try {
        const res = await fetch('/api/topology');
        const json = await res.json();

        const rawLinks = json.data || [];

        // Extract unique nodes
        const nodeSet = new Set<string>();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rawLinks.forEach((link: any) => {
          nodeSet.add(link.parent);
          nodeSet.add(link.child);
        });

        // Ensure fallback nodes are present if empty
        if (nodeSet.size === 0) {
          ['frontend-service', 'auth-service', 'cart-service', 'payment-service'].forEach(n => nodeSet.add(n));
        }

        const nodes: GraphNode[] = Array.from(nodeSet).map(id => ({
          id,
          name: id,
          val: id === 'frontend-service' ? 2 : 1, // Make frontend slightly larger
          color: '#10b981', // green-500
          status: 'healthy',
        }));

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const links: GraphLink[] = rawLinks.map((link: any) => ({
          source: link.parent,
          target: link.child,
          value: link.callCount || 1,
        }));

        setGraphData({ nodes, links });
        addLog(`Loaded topology with ${nodes.length} nodes.`, 'info');
      } catch (err) {
        console.error("Failed to load topology", err);
        addLog("Failed to load topology. Using fallback.", 'error');
      }
    }

    fetchTopology();
  }, [addLog]);

  const updateNodeStatus = useCallback((serviceId: string, status: 'healthy' | 'failing' | 'recovering') => {
    setGraphData(prev => {
      const newNodes = prev.nodes.map(node => {
        if (node.id === serviceId) {
          return {
            ...node,
            status,
            color: status === 'failing' ? '#ef4444' : // red-500
              status === 'recovering' ? '#eab308' : // yellow-500
                '#10b981', // green-500
          };
        }
        return node;
      });
      return { ...prev, nodes: newNodes };
    });
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleIncomingEvent = useCallback((data: any) => {
    if (!data.service) return;

    if (data.action === 'restart_container' || data.type === 'remediation') {
      const cause = data.root_cause || 'Unknown';
      const confidence = data.confidence ? ` (${Math.round(data.confidence * 100)}% confidence)` : '';
      addLog(`🔴 ANOMALY: ${data.service} — RCA: "${cause}"${confidence}`, 'error');
      addLog(`⚙️  ACTION: Restarting ${data.service} via Docker socket...`, 'error');
      updateNodeStatus(data.service, 'failing');

      setTimeout(() => {
        addLog(`🟡 RECOVERING: ${data.service} container restarting...`, 'info');
        updateNodeStatus(data.service, 'recovering');

        setTimeout(() => {
          addLog(`✅ HEALTHY: ${data.service} successfully restarted.`, 'success');
          updateNodeStatus(data.service, 'healthy');
        }, 2000);
      }, 4000);
    } else if (data.severity === 'critical') {
      addLog(`⚠️  ALERT: ${data.service} — ${data.metric || 'Unknown anomaly'} exceeded threshold`, 'error');
      updateNodeStatus(data.service, 'failing');
    }
  }, [updateNodeStatus, addLog]);

  // Set up SSE listener
  useEffect(() => {
    addLog('Connecting to SSE stream...', 'info');

    // Use the native EventSource API
    const evtSource = new EventSource('/api/events');

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'ping') {
          console.log('SSE Ping received');
          return;
        }

        handleIncomingEvent(data);
      } catch (err) {
        console.error("Error parsing SSE data", err);
      }
    };

    evtSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      // addLog('SSE connection lost. Reconnecting...', 'error');
      // EventSource auto-reconnects, but we might want to track state
    };

    return () => {
      evtSource.close();
    };
  }, [handleIncomingEvent, addLog]); // Only connect once, handleIncomingEvent is memoized

  // Demo Mode Handler — fully randomized fault scenarios
  const triggerDemoChaos = () => {
    const targets = ['payment-service', 'cart-service', 'auth-service'];
    const faultScenarios = [
      { metric: 'http_request_duration_seconds', root_cause: 'DB Timeout / Connection Refused', confidence: 0.95 },
      { metric: 'http_requests_total', root_cause: 'Internal Server Error / Exception', confidence: 0.90 },
      { metric: 'http_request_duration_seconds', root_cause: 'Memory Leak / OOM Killer', confidence: 0.95 },
      { metric: 'http_requests_total', root_cause: 'Upstream Service Timeout', confidence: 0.85 },
      { metric: 'http_request_duration_seconds', root_cause: 'Disk I/O Saturation', confidence: 0.80 },
    ];

    const randomTarget = targets[Math.floor(Math.random() * targets.length)];
    const scenario = faultScenarios[Math.floor(Math.random() * faultScenarios.length)];

    addLog(`[DEMO] Prometheus alert firing: ${scenario.metric} exceeded threshold on ${randomTarget}`, 'info');
    addLog(`[DEMO] Alertmanager → RCA Engine webhook dispatched`, 'info');

    setTimeout(() => {
      handleIncomingEvent({
        service: randomTarget,
        metric: scenario.metric,
        severity: 'critical',
        timestamp: new Date().toISOString()
      });

      // Simulate the 3s RCA micro-buffer then remediation
      setTimeout(() => {
        addLog(`[DEMO] RCA Engine: 3s ingestion buffer complete. Querying Loki...`, 'info');
        setTimeout(() => {
          handleIncomingEvent({
            service: randomTarget,
            action: 'restart_container',
            root_cause: scenario.root_cause,
            confidence: scenario.confidence,
            timestamp: new Date().toISOString()
          });
        }, 1500);
      }, 3000);
    }, 1000);
  };

  // Node rendering with pulse effect for failing nodes
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const n = node as GraphNode;
    const label = n.name;
    const fontSize = 12 / globalScale;
    ctx.font = `${fontSize}px Sans-Serif`;
    // const textWidth = ctx.measureText(label).width;
    // const bckgDimensions = [textWidth + fontSize * 0.2, fontSize * 1.2]; // some padding

    // Draw background/node
    const nodeRadius = n.val * 4;

    if (n.status === 'failing') {
      // Pulse effect RED
      const t = Date.now() / 200;
      const pulseRadius = nodeRadius + Math.sin(t) * 2 + 2;
      ctx.beginPath();
      ctx.arc(n.x!, n.y!, pulseRadius, 0, 2 * Math.PI, false);
      ctx.fillStyle = 'rgba(239, 68, 68, 0.4)'; // red with alpha
      ctx.fill();
    } else if (n.status === 'recovering') {
      // Pulse effect GREEN
      const t = Date.now() / 200;
      const pulseRadius = nodeRadius + Math.sin(t) * 2 + 2;
      ctx.beginPath();
      ctx.arc(n.x!, n.y!, pulseRadius, 0, 2 * Math.PI, false);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.4)'; // green with alpha
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(n.x!, n.y!, nodeRadius, 0, 2 * Math.PI, false);
    ctx.fillStyle = n.color;
    ctx.fill();

    // Border
    ctx.strokeStyle = '#1f2937'; // gray-800
    ctx.lineWidth = 1 / globalScale;
    ctx.stroke();

    // Draw text
    ctx.fillStyle = '#f3f4f6'; // gray-100
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, n.x!, n.y! + nodeRadius + fontSize);
  }, []);

  // Force re-render to animate pulse without reheating simulation
  useEffect(() => {
    const hasAnimatedNodes = graphData.nodes.some(n => n.status === 'failing' || n.status === 'recovering');
    if (!hasAnimatedNodes) return;

    let animationFrameId: number;
    const animate = () => {
      // Just manually trigger a canvas redraw instead of physics update
      setGraphData(prev => ({ ...prev }));
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();
    return () => cancelAnimationFrame(animationFrameId);
  }, [graphData.nodes]);


  return (
    <div className="flex h-screen w-full bg-gray-950 text-gray-100 overflow-hidden font-sans">
      {/* Sidebar / Logs */}
      <div className="w-1/3 min-w-[350px] flex flex-col border-r border-gray-800 bg-gray-900 shadow-xl z-10">
        <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-950">
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            Real-Time AI RCA
          </h1>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Live System</span>
          </div>
        </div>

        <div className="p-4 flex flex-col gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 className="text-sm text-gray-400 font-semibold mb-2 uppercase tracking-wide">Control Panel</h2>
            <button
              onClick={triggerDemoChaos}
              className="w-full py-2 px-4 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white rounded font-medium transition-all shadow-lg shadow-red-900/20 flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m11 7-3.2 3.2a1.1 1.1 0 0 0 0 1.6l4.4 4.4a1.1 1.1 0 0 0 1.6 0L17 13" /><path d="m2 22 20-20" /><path d="m15 15-2-2" /></svg>
              Activate Demo Chaos
            </button>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Mocks an Alertmanager webhook & RCA execution.
            </p>
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="p-2 border-b border-gray-800 bg-gray-900 flex justify-between items-center">
            <h2 className="text-xs text-gray-400 font-semibold uppercase tracking-wide px-2">Event Stream Terminal</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4 bg-black font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-gray-600 italic">Waiting for telemetry...</div>
            ) : (
              <ul className="space-y-2 flex flex-col justify-end min-h-full">
                {logs.map((log, i) => (
                  <li key={i} className={`pb-1 ${log.type === 'error' ? 'text-red-400' :
                      log.type === 'success' ? 'text-green-400' :
                        'text-gray-300'
                    }`}>
                    <span className="text-gray-600 mr-2">[{log.timestamp}]</span>
                    {log.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Graph Area */}
      <div className="flex-1 relative" ref={containerRef}>
        <div className="absolute top-4 left-4 z-10 bg-gray-900/80 backdrop-blur border border-gray-700 rounded-md p-3 shadow-lg">
          <h3 className="text-sm font-semibold text-gray-200 mb-2">Service Topology</h3>
          <div className="flex flex-col gap-2 text-xs">
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500"></div><span className="text-gray-400">Healthy</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div><span className="text-gray-400">Anomaly / Remediation</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-yellow-500"></div><span className="text-gray-400">Recovering / Booting</span></div>
          </div>
        </div>

        {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={fgRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeLabel="name"
            nodeRelSize={6}
            linkColor={() => 'rgba(255,255,255,0.2)'}
            linkWidth={1.5}
            nodeCanvasObject={paintNode}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            backgroundColor="#030712" // bg-gray-950
          />
        )}
      </div>
    </div>
  );
}
