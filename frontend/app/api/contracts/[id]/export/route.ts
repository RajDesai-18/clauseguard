import type { NextRequest } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface RouteContext {
  params: Promise<{ id: string }>;
}

/**
 * Proxy route for the contract review DOCX export.
 *
 * Forwards the browser's session cookie to the FastAPI backend, then
 * streams the response back to the browser. Keeping the request
 * same-origin from the browser's perspective avoids the cross-origin
 * cookie and CORS dance for a downloaded file.
 *
 * The browser hits this with a plain <a href download>, so we need
 * to return the docx bytes with their original Content-Type and
 * Content-Disposition headers intact.
 */
export async function GET(_req: NextRequest, { params }: RouteContext) {
  const { id } = await params;

  if (!isValidUuid(id)) {
    return new Response("Invalid contract id", { status: 400 });
  }

  const jar = await cookies();
  const cookieHeader = jar
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/api/v1/contracts/${id}/export`, {
      method: "GET",
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      cache: "no-store",
    });
  } catch (err) {
    return new Response(
      `Failed to reach backend: ${err instanceof Error ? err.message : String(err)}`,
      { status: 502 }
    );
  }

  if (!upstream.ok) {
    // Surface backend status (401, 404, 409) directly so the browser
    // download fails meaningfully instead of saving an HTML error page.
    return new Response(upstream.statusText || "Export failed", {
      status: upstream.status,
    });
  }

  // Forward the streaming body with the headers the backend set, so
  // the browser sees the original filename and content type.
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  const contentDisposition = upstream.headers.get("content-disposition");
  const contentLength = upstream.headers.get("content-length");
  if (contentType) headers.set("Content-Type", contentType);
  if (contentDisposition) headers.set("Content-Disposition", contentDisposition);
  if (contentLength) headers.set("Content-Length", contentLength);
  headers.set("Cache-Control", "no-store");

  return new Response(upstream.body, {
    status: 200,
    headers,
  });
}

function isValidUuid(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}