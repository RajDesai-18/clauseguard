import type { NextRequest } from "next/server";
import Redis from "ioredis";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REDIS_URL = process.env.REDIS_URL ?? "redis://localhost:6379/0";
const CHANNEL_PREFIX = "contract:progress:";
const HEARTBEAT_INTERVAL_MS = 20_000;

interface RouteContext {
  params: Promise<{ id: string }>;
}

export async function GET(req: NextRequest, { params }: RouteContext) {
  const { id } = await params;

  if (!isValidUuid(id)) {
    return new Response("Invalid contract id", { status: 400 });
  }

  const channel = `${CHANNEL_PREFIX}${id}`;
  const subscriber = new Redis(REDIS_URL, {
    lazyConnect: true,
    maxRetriesPerRequest: 3,
  });

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let heartbeat: ReturnType<typeof setInterval> | null = null;
      let closed = false;

      const safeEnqueue = (chunk: string) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(chunk));
        } catch {
          closed = true;
        }
      };

      const cleanup = async () => {
        if (closed) return;
        closed = true;
        if (heartbeat) clearInterval(heartbeat);
        try {
          await subscriber.unsubscribe(channel);
        } catch {
          // ignore
        }
        try {
          subscriber.disconnect();
        } catch {
          // ignore
        }
        try {
          controller.close();
        } catch {
          // ignore
        }
      };

      try {
        await subscriber.connect();
        await subscriber.subscribe(channel);
      } catch (err) {
        safeEnqueue(
          `event: error\ndata: ${JSON.stringify({
            message: "Failed to subscribe to progress channel",
            error: err instanceof Error ? err.message : String(err),
          })}\n\n`
        );
        await cleanup();
        return;
      }

      subscriber.on("message", (_channel, message) => {
        safeEnqueue(`data: ${message}\n\n`);
      });

      subscriber.on("error", (err) => {
        safeEnqueue(
          `event: error\ndata: ${JSON.stringify({
            message: "Redis connection error",
            error: err.message,
          })}\n\n`
        );
      });

      // Initial connection event so the client knows the stream is live
      safeEnqueue(`event: connected\ndata: {"channel":"${channel}"}\n\n`);

      // Heartbeat to keep the connection open through proxies/load balancers
      heartbeat = setInterval(() => {
        safeEnqueue(": heartbeat\n\n");
      }, HEARTBEAT_INTERVAL_MS);

      // Clean up when the client disconnects
      req.signal.addEventListener("abort", () => {
        void cleanup();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

function isValidUuid(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}
