import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(request: NextRequest) {
  const endpoint = process.env.BACKEND_URL;
  if (!endpoint) return Response.json({ error: "Backend unavailable" }, { status: 503 });
  try {
    const response = await fetch(`${endpoint}/notes`, {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      body: request.method === "POST" ? await request.text() : undefined,
      cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    return new Response(await response.text(), { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch { return Response.json({ error: "Backend unavailable" }, { status: 503 }); }
}
export const GET = proxy;
export const POST = proxy;
