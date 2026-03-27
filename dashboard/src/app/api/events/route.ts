import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// In-memory array of clients waiting for SSE messages
let clients: ReadableStreamDefaultController[] = [];

// Handle GET to stream SSE
export async function GET(req: NextRequest) {
  const stream = new ReadableStream({
    start(controller) {
      clients.push(controller);
      console.log(`New SSE client connected. Total clients: ${clients.length}`);

      // Send an initial ping to establish connection
      controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ type: "ping", timestamp: new Date().toISOString() })}\n\n`));

      // Cleanup when connection closes
      req.signal.addEventListener("abort", () => {
        clients = clients.filter(c => c !== controller);
        console.log(`SSE client disconnected. Total clients: ${clients.length}`);
      });
    }
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
    },
  });
}

// Handle POST to broadcast a new event to all connected SSE clients
export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    console.log("Received RCA/Remediation event:", payload);

    // Format the SSE message
    const message = `data: ${JSON.stringify(payload)}\n\n`;
    const encodedMessage = new TextEncoder().encode(message);

    // Broadcast to all active clients
    clients.forEach(client => {
      try {
        client.enqueue(encodedMessage);
      } catch (err) {
        console.error("Failed to enqueue message to client", err);
      }
    });

    return NextResponse.json({ success: true, broadcastedTo: clients.length }, { status: 200 });
  } catch (error) {
    console.error("Error broadcasting event:", error);
    return NextResponse.json({ success: false, error: "Invalid payload" }, { status: 400 });
  }
}
