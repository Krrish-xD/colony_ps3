import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const JAEGER_URL = process.env.JAEGER_URL || "http://jaeger:16686";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function GET(_req: NextRequest) {
  try {
    // Attempt to fetch dependencies from Jaeger
    const res = await fetch(`${JAEGER_URL}/api/dependencies?endTs=${Date.now()}`, {
      // Short timeout for demo purposes
      signal: AbortSignal.timeout(2000),
    });

    if (!res.ok) {
      throw new Error(`Jaeger returned ${res.status}`);
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.warn("Failed to fetch from Jaeger, returning fallback topology:", error);

    // Provide immediate clean static fallback array if Jaeger API fails
    const fallbackTopology = {
      data: [
        { parent: "frontend-service", child: "auth-service", callCount: 1 },
        { parent: "frontend-service", child: "cart-service", callCount: 1 },
        { parent: "frontend-service", child: "payment-service", callCount: 1 },
      ]
    };

    return NextResponse.json(fallbackTopology);
  }
}
